from utilities.choices import ChoiceSet


#
# Import Choices
#

class ImportFormatChoices(ChoiceSet):
    CSV = 'csv'
    JSON = 'json'
    YAML = 'yaml'

    CHOICES = [
        (CSV, 'CSV'),
        (JSON, 'JSON'),
        (YAML, 'YAML'),
    ]


class ImportFormatChoicesRelated(ChoiceSet):
    JSON = 'json'
    YAML = 'yaml'

    CHOICES = [
        (JSON, 'JSON'),
        (YAML, 'YAML'),
    ]
