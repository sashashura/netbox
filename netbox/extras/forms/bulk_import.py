from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.forms import SimpleArrayField
from django.utils.safestring import mark_safe

from extras.choices import CustomFieldVisibilityChoices, CustomFieldTypeChoices
from extras.models import *
from extras.utils import FeatureQuery
from utilities.forms import CSVChoiceField, CSVContentTypeField, CSVModelForm, CSVMultipleContentTypeField, SlugField

__all__ = (
    'CustomFieldCSVForm',
    'CustomLinkCSVForm',
    'ExportTemplateCSVForm',
    'TagCSVForm',
    'WebhookCSVForm',
)


class CustomFieldCSVForm(CSVModelForm):
    content_types = CSVMultipleContentTypeField(
        queryset=ContentType.objects.all(),
        limit_choices_to=FeatureQuery('custom_fields'),
        help_text="One or more assigned object types"
    )
    type = CSVChoiceField(
        choices=CustomFieldTypeChoices,
        help_text='Field data type (e.g. text, integer, etc.)'
    )
    object_type = CSVContentTypeField(
        queryset=ContentType.objects.all(),
        limit_choices_to=FeatureQuery('custom_fields'),
        required=False,
        help_text="Object type (for object or multi-object fields)"
    )
    choices = SimpleArrayField(
        base_field=forms.CharField(),
        required=False,
        help_text='Comma-separated list of field choices'
    )
    ui_visibility = CSVChoiceField(
        choices=CustomFieldVisibilityChoices,
        help_text='How the custom field is displayed in the user interface'
    )

    class Meta:
        model = CustomField
        fields = (
            'name', 'label', 'group_name', 'type', 'content_types', 'object_type', 'required', 'description', 'weight',
            'filter_logic', 'default', 'choices', 'weight', 'validation_minimum', 'validation_maximum',
            'validation_regex', 'ui_visibility',
        )


class CustomLinkCSVForm(CSVModelForm):
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.all(),
        limit_choices_to=FeatureQuery('custom_links'),
        help_text="Assigned object type"
    )

    class Meta:
        model = CustomLink
        fields = (
            'name', 'content_type', 'enabled', 'weight', 'group_name', 'button_class', 'new_window', 'link_text',
            'link_url',
        )


class ExportTemplateCSVForm(CSVModelForm):
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.all(),
        limit_choices_to=FeatureQuery('export_templates'),
        help_text="Assigned object type"
    )

    class Meta:
        model = ExportTemplate
        fields = (
            'name', 'content_type', 'description', 'mime_type', 'file_extension', 'as_attachment', 'template_code',
        )


class WebhookCSVForm(CSVModelForm):
    content_types = CSVMultipleContentTypeField(
        queryset=ContentType.objects.all(),
        limit_choices_to=FeatureQuery('webhooks'),
        help_text="One or more assigned object types"
    )

    class Meta:
        model = Webhook
        fields = (
            'name', 'enabled', 'content_types', 'type_create', 'type_update', 'type_delete', 'payload_url',
            'http_method', 'http_content_type', 'additional_headers', 'body_template', 'secret', 'ssl_verification',
            'ca_file_path'
        )


class TagCSVForm(CSVModelForm):
    slug = SlugField()

    class Meta:
        model = Tag
        fields = ('name', 'slug', 'color', 'description')
        help_texts = {
            'color': mark_safe('RGB color in hexadecimal (e.g. <code>00ff00</code>)'),
        }
