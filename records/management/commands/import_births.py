import csv
from django.core.management.base import BaseCommand
from records.models import Record, BirthRecord


class Command(BaseCommand):
    help = 'Import birth records from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument(
            '--record-title',
            type=str,
            default='Södra Ny Parish Birth Records 1783-1823',
            help='Title for the Record entry'
        )
        parser.add_argument(
            '--record-description',
            type=str,
            default='Birth records from Södra Ny parish, Sweden, covering the years 1783-1823.',
            help='Description for the Record entry'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        record_title = options['record_title']
        record_description = options['record_description']

        # Create or get the Record entry
        record, created = Record.objects.get_or_create(
            title=record_title,
            defaults={
                'description': record_description,
                'source': 'Södra Ny kyrkoarkiv',
                'date_range': '1783-1823',
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Record: {record.title}'))
        else:
            self.stdout.write(self.style.WARNING(f'Using existing Record: {record.title}'))

        # Read and import CSV
        imported_count = 0
        skipped_count = 0

        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    try:
                        # Map Swedish column names to English field names
                        sex = 'M' if row.get('Kön', '').lower() == 'man' else 'F' if row.get('Kön', '').lower() == 'kvinna' else 'U'
                        
                        # Parse birth year
                        birth_year_str = row.get('Födelseår', '').strip()
                        if not birth_year_str:
                            self.stdout.write(self.style.WARNING(f'Skipping row with no birth year: {row.get("Förnamn", "Unknown")}'))
                            skipped_count += 1
                            continue
                        
                        birth_year = int(birth_year_str)
                        
                        # Parse optional integer fields
                        father_birth_year = None
                        if row.get('Fader födelseår', '').strip():
                            try:
                                father_birth_year = int(row['Fader födelseår'])
                            except ValueError:
                                pass
                        
                        mother_birth_year = None
                        if row.get('Moder födelseår', '').strip():
                            try:
                                mother_birth_year = int(row['Moder födelseår'])
                            except ValueError:
                                pass
                        
                        # Create BirthRecord
                        BirthRecord.objects.create(
                            record=record,
                            first_name=row.get('Förnamn', '').strip(),
                            sex=sex,
                            birth_date=row.get('Födelsedatum', '').strip(),
                            birth_year=birth_year,
                            location=row.get('Ort', '').strip(),
                            father_first_name=row.get('Fader förnamn', '').strip(),
                            father_last_name=row.get('Fader efternamn', '').strip(),
                            father_birth_year=father_birth_year,
                            father_birth_parish=row.get('Fader födelsesocken', '').strip(),
                            mother_first_name=row.get('Moder förnamn', '').strip(),
                            mother_last_name=row.get('Moder efternamn', '').strip(),
                            mother_birth_year=mother_birth_year,
                            mother_birth_parish=row.get('Moder födelsesocken', '').strip(),
                            archive_info=row.get('Arkivinfo', '').strip(),
                            link=row.get('Länk', '').strip(),
                            notes=row.get('Övrigt', '').strip(),
                        )
                        
                        imported_count += 1
                        
                        if imported_count % 50 == 0:
                            self.stdout.write(f'Imported {imported_count} records...')
                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error importing row: {str(e)}'))
                        skipped_count += 1
                        continue

            self.stdout.write(self.style.SUCCESS(f'\nImport completed!'))
            self.stdout.write(self.style.SUCCESS(f'Successfully imported: {imported_count} records'))
            if skipped_count > 0:
                self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count} records'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading CSV file: {str(e)}'))
