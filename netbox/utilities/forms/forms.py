import csv
import json
import re
from io import StringIO

import yaml
from django import forms
from utilities.forms.utils import parse_csv, validate_csv

from .choices import ImportFormatChoices, ImportFormatChoicesRelated
from .widgets import APISelect, APISelectMultiple, ClearableFileInput, StaticSelect

__all__ = (
    'BootstrapMixin',
    'BulkEditForm',
    'BulkRenameForm',
    'ConfirmationForm',
    'CSVModelForm',
    'FilterForm',
    'ImportForm',
    'FileUploadImportForm',
    'ReturnURLForm',
    'TableConfigForm',
)


#
# Mixins
#

class BootstrapMixin:
    """
    Add the base Bootstrap CSS classes to form elements.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        exempt_widgets = [
            forms.CheckboxInput,
            forms.FileInput,
            forms.RadioSelect,
            forms.Select,
            APISelect,
            APISelectMultiple,
            ClearableFileInput,
            StaticSelect,
        ]

        for field_name, field in self.fields.items():

            if field.widget.__class__ not in exempt_widgets:
                css = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = ' '.join([css, 'form-control']).strip()

            if field.required and not isinstance(field.widget, forms.FileInput):
                field.widget.attrs['required'] = 'required'

            if 'placeholder' not in field.widget.attrs and field.label is not None:
                field.widget.attrs['placeholder'] = field.label

            if field.widget.__class__ == forms.CheckboxInput:
                css = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = ' '.join((css, 'form-check-input')).strip()

            if field.widget.__class__ == forms.Select:
                css = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = ' '.join((css, 'form-select')).strip()


#
# Form classes
#

class ReturnURLForm(forms.Form):
    """
    Provides a hidden return URL field to control where the user is directed after the form is submitted.
    """
    return_url = forms.CharField(required=False, widget=forms.HiddenInput())


class ConfirmationForm(BootstrapMixin, ReturnURLForm):
    """
    A generic confirmation form. The form is not valid unless the confirm field is checked.
    """
    confirm = forms.BooleanField(required=True, widget=forms.HiddenInput(), initial=True)


class BulkEditForm(BootstrapMixin, forms.Form):
    """
    Provides bulk edit support for objects.
    """
    nullable_fields = ()


class BulkRenameForm(BootstrapMixin, forms.Form):
    """
    An extendable form to be used for renaming objects in bulk.
    """
    find = forms.CharField()
    replace = forms.CharField(
        required=False
    )
    use_regex = forms.BooleanField(
        required=False,
        initial=True,
        label='Use regular expressions'
    )

    def clean(self):
        super().clean()

        # Validate regular expression in "find" field
        if self.cleaned_data['use_regex']:
            try:
                re.compile(self.cleaned_data['find'])
            except re.error:
                raise forms.ValidationError({
                    'find': "Invalid regular expression"
                })


class CSVModelForm(forms.ModelForm):
    """
    ModelForm used for the import of objects in CSV format.
    """

    def __init__(self, *args, headers=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Modify the model form to accommodate any customized to_field_name properties
        if headers:
            for field, to_field in headers.items():
                if to_field is not None:
                    self.fields[field].to_field_name = to_field


class BaseImportForm(BootstrapMixin, forms.Form):

    def __init__(self, *args, **kwargs):
        related = kwargs.pop("related", False)
        super().__init__(*args, **kwargs)
        if related:
            self.fields['format'].choices = ImportFormatChoicesRelated.CHOICES
            self.fields['format'].initial = ImportFormatChoicesRelated.YAML

    def convert_data(self, data):
        format = self.cleaned_data['format']
        stream = StringIO(data.strip())

        # Process data
        if format == ImportFormatChoices.CSV:
            reader = csv.reader(stream)
            headers, records = parse_csv(reader)
            self.cleaned_data['data'] = records
            self.cleaned_data['headers'] = headers
        elif format == ImportFormatChoices.JSON:
            try:
                self.cleaned_data['data'] = json.loads(data)
            except json.decoder.JSONDecodeError as err:
                raise forms.ValidationError({
                    'data': f"Invalid JSON data: {err}"
                })
        elif format == ImportFormatChoices.YAML:
            try:
                self.cleaned_data['data'] = yaml.load_all(data, Loader=yaml.SafeLoader)
            except yaml.error.YAMLError as err:
                raise forms.ValidationError({
                    'data': f"Invalid YAML data: {err}"
                })
        else:
            raise forms.ValidationError({
                'data': f"Invalid file format: {format}"
            })


class ImportForm(BaseImportForm):
    """
    Generic form for creating an object from JSON/YAML data
    """
    data = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'font-monospace'}),
        help_text="Enter object data in CSV, JSON or YAML format."
    )
    format = forms.ChoiceField(
        choices=ImportFormatChoices.CHOICES,
        initial=ImportFormatChoices.CSV
    )

    def clean(self):
        super().clean()

        data = self.cleaned_data['data'] if 'data' in self.cleaned_data else None
        self.convert_data(data)


class FileUploadImportForm(BaseImportForm):
    """
    Generic form for creating an object from JSON/YAML data
    """
    data_file = forms.FileField(
        label="data file",
        required=False
    )
    format = forms.ChoiceField(
        choices=ImportFormatChoices.CHOICES,
        initial=ImportFormatChoices.CSV
    )

    def clean(self):
        super().clean()

        file = self.files.get('data_file')

        data = file.read().decode('utf-8')
        self.convert_data(data)


class FilterForm(BootstrapMixin, forms.Form):
    """
    Base Form class for FilterSet forms.
    """
    q = forms.CharField(
        required=False,
        label='Search'
    )


class TableConfigForm(BootstrapMixin, forms.Form):
    """
    Form for configuring user's table preferences.
    """
    available_columns = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(
            attrs={'size': 10, 'class': 'form-select'}
        ),
        label='Available Columns'
    )
    columns = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(
            attrs={'size': 10, 'class': 'form-select'}
        ),
        label='Selected Columns'
    )

    def __init__(self, table, *args, **kwargs):
        self.table = table

        super().__init__(*args, **kwargs)

        # Initialize columns field based on table attributes
        self.fields['available_columns'].choices = table.available_columns
        self.fields['columns'].choices = table.selected_columns

    @property
    def table_name(self):
        return self.table.__class__.__name__
