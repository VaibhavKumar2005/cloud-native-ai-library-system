from django.db import migrations, models


def backfill_document_status(apps, schema_editor):
    Document = apps.get_model('ai_engine', 'Document')
    for document in Document.objects.all():
        if document.processed:
            document.status = 'indexed'
            document.progress_percent = 100
        else:
            document.status = 'queued'
            document.progress_percent = 0
        document.total_chunks = 0
        document.processed_chunks = 0
        document.last_error = ''
        document.save(update_fields=[
            'status',
            'progress_percent',
            'total_chunks',
            'processed_chunks',
            'last_error',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('ai_engine', '0002_document_user_alter_document_file_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    """
                    ALTER TABLE ai_engine_document
                    ADD COLUMN IF NOT EXISTS last_error text DEFAULT '';
                    """,
                    reverse_sql="""
                    ALTER TABLE ai_engine_document
                    DROP COLUMN IF EXISTS last_error;
                    """,
                ),
                migrations.RunSQL(
                    """
                    ALTER TABLE ai_engine_document
                    ADD COLUMN IF NOT EXISTS processed_chunks integer DEFAULT 0;
                    """,
                    reverse_sql="""
                    ALTER TABLE ai_engine_document
                    DROP COLUMN IF EXISTS processed_chunks;
                    """,
                ),
                migrations.RunSQL(
                    """
                    ALTER TABLE ai_engine_document
                    ADD COLUMN IF NOT EXISTS progress_percent smallint DEFAULT 0;
                    """,
                    reverse_sql="""
                    ALTER TABLE ai_engine_document
                    DROP COLUMN IF EXISTS progress_percent;
                    """,
                ),
                migrations.RunSQL(
                    """
                    ALTER TABLE ai_engine_document
                    ADD COLUMN IF NOT EXISTS status varchar(20) DEFAULT 'queued';
                    """,
                    reverse_sql="""
                    ALTER TABLE ai_engine_document
                    DROP COLUMN IF EXISTS status;
                    """,
                ),
                migrations.RunSQL(
                    """
                    ALTER TABLE ai_engine_document
                    ADD COLUMN IF NOT EXISTS total_chunks integer DEFAULT 0;
                    """,
                    reverse_sql="""
                    ALTER TABLE ai_engine_document
                    DROP COLUMN IF EXISTS total_chunks;
                    """,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='document',
                    name='last_error',
                    field=models.TextField(blank=True, default=''),
                ),
                migrations.AddField(
                    model_name='document',
                    name='processed_chunks',
                    field=models.PositiveIntegerField(default=0),
                ),
                migrations.AddField(
                    model_name='document',
                    name='progress_percent',
                    field=models.PositiveSmallIntegerField(default=0),
                ),
                migrations.AddField(
                    model_name='document',
                    name='status',
                    field=models.CharField(
                        choices=[('queued', 'Queued'), ('indexing', 'Indexing'), ('indexed', 'Indexed'), ('failed', 'Failed')],
                        default='queued',
                        max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name='document',
                    name='total_chunks',
                    field=models.PositiveIntegerField(default=0),
                ),
            ],
        ),
        migrations.RunPython(backfill_document_status, migrations.RunPython.noop),
    ]
