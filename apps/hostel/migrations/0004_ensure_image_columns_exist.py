from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("hostel", "0003_area_image_building_image_cot_image_floor_image_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                """
                ALTER TABLE hostel_area
                ADD COLUMN IF NOT EXISTS image varchar(100);
                """,
                """
                ALTER TABLE hostel_building
                ADD COLUMN IF NOT EXISTS image varchar(100);
                """,
                """
                ALTER TABLE hostel_section
                ADD COLUMN IF NOT EXISTS image varchar(100);
                """,
                """
                ALTER TABLE hostel_floor
                ADD COLUMN IF NOT EXISTS image varchar(100);
                """,
                """
                ALTER TABLE hostel_room
                ADD COLUMN IF NOT EXISTS image varchar(100);
                """,
                """
                ALTER TABLE hostel_cot
                ADD COLUMN IF NOT EXISTS image varchar(100);
                """,
            ],
            reverse_sql=[
                """
                ALTER TABLE hostel_area
                DROP COLUMN IF EXISTS image;
                """,
                """
                ALTER TABLE hostel_building
                DROP COLUMN IF EXISTS image;
                """,
                """
                ALTER TABLE hostel_section
                DROP COLUMN IF EXISTS image;
                """,
                """
                ALTER TABLE hostel_floor
                DROP COLUMN IF EXISTS image;
                """,
                """
                ALTER TABLE hostel_room
                DROP COLUMN IF EXISTS image;
                """,
                """
                ALTER TABLE hostel_cot
                DROP COLUMN IF EXISTS image;
                """,
            ],
        ),
    ]
