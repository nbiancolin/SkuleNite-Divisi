# Generated manually

from django.db import migrations, models


def _default_formatting_steps_migration():
    """Inline default so migrate does not depend on musescore_part_formatter import path."""
    return {k: True for k in _FORMATTING_STEP_KEYS}


_FORMATTING_STEP_KEYS = (
    "apply_mss_style",
    "apply_score_metadata",
    "apply_multimeasure_rest_prep",
    "apply_rehearsal_line_breaks",
    "apply_double_bar_line_breaks",
    "apply_measure_count_line_breaks",
    "apply_line_break_balancing",
    "apply_multimeasure_rest_cleanup",
    "apply_broadway_vbox_header",
    "apply_part_name_in_header",
)


class Migration(migrations.Migration):

    dependencies = [
        ("ensembles", "0033_commit_created_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="arrangementversion",
            name="formatting_steps",
            field=models.JSONField(default=_default_formatting_steps_migration),
        ),
    ]
