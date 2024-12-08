import argparse
import io
import os
import re

from genealogy.models import Child, Family, Individual, Tree
import genealogy.date_functions as df

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
GEDFILE = os.path.join(CURRENT_DIR, 'Danielsson-1.ged')

# HEAD
HEAD_REGEX = re.compile('^([0-9]) HEAD')
TREE_REGEX = re.compile('^([0-9]) _TREE (.*)')

# INDI
INDI_REGEX = re.compile('^([0-9]) (@I[0-9]+@) INDI')
NAME_REGEX = re.compile('^([0-9]) NAME')
GIVN_REGEX = re.compile('^([0-9]) GIVN (.*)')
SURN_REGEX = re.compile('^([0-9]) SURN (.*)')
FAMS_REGEX = re.compile('^([0-9]) FAMS (@F[0-9]+@)')
FAMC_REGEX = re.compile('^([0-9]) FAMC (@F[0-9]+@)')
SEX_REGEX = re.compile('([0-9]) SEX ([F|M])')
BIRT_REGEX = re.compile('([0-9]) BIRT')
DEAT_REGEX = re.compile('([0-9]) DEAT')
DATE_REGEX = re.compile('([0-9]) DATE (.*)')
PLAC_REGEX = re.compile('([0-9]) PLAC (.*)')
DCAUSE_REGEX = re.compile('[0-9] _DCAUSE')
NOTE_REGEX = re.compile('([0-9]) NOTE (.*)')

# FAM
FAM_REGEX = re.compile('^([0-9]) (@F[0-9]+@) FAM')
WIFE_REGEX = re.compile('([0-9]) WIFE (@I[0-9]+@)')
HUSB_REGEX = re.compile('([0-9]) HUSB (@I[0-9]+@)')
CHIL_REGEX = re.compile('([0-9]) CHIL (@I[0-9]+@)')
MARR_REGEX = re.compile('([0-9]) MARR')
DIV_REGEX = re.compile('([0-9]) DIV')


class Ind:
    def __init__(self, indi_id):
        self.id = indi_id
        self.sex = ''
        self.given_name = ''
        self.surname = ''
        self.fams = ''
        self.famc = ''
        self.birth = {'date': None, 'place': None, 'year': None}
        self.death = {'date': None, 'place': None, 'cause': '', 'year': None}

    def get_name(self):
        return f"{self.get_given_name()} {self.get_surname()}"

    def get_given_name(self):
        return self.given_name if self.given_name else ''

    def get_surname(self):
        return self.surname if self.surname else ''

    def get_sex(self):
        mapping = {
            'M' : 'Man',
            'F' : 'Kvinna',
            'U' : 'Okänt',
        }
        return mapping[self.sex]

    def get_birth_date(self):
        return self.birth['date']

    def get_birth_place(self, no_country=True):
        if no_country:
            return self.birth['place'].removesuffix(', Sverige')
        else:
            return self.birth['place']

    def get_death_date(self):
        return self.death['date']

    def get_death_place(self, no_country=True):
        if no_country:
            return self.death['place'].removesuffix(', Sverige')
        else:
            return self.death['place']

    def get_death_cause(self):
        return self.death['cause']

    def __str__(self):
        return 'Namn: {} {}\nKön: {}\nFödelsedatum: {}\nFödelseplats: {}\nDödsdatum: {}\nDödsplats: {}\n'.format(
                    self.given_name, self.surname, self.sex, self.birth['date'], self.birth['place'],
                    self.death['date'], self.death['place'])


class FamilyGC:
    def __init__(self, fam_id):
        self.id = fam_id
        self.husband = ''
        self.wife = ''
        self.children = []
        self.marriage = {'date': None, 'place': None}
        self.divorce = {'date': None, 'place': None}


class Gedcom:
    def __init__(self, file=GEDFILE):
        self.name = ""
        self.individuals = {}
        self.families = {}

        self.setup(file)

    def setup(self, file):
        with io.open(file, mode='r', encoding='utf-8') as f:
            lines = f.readlines()

        for index, line in enumerate(lines):
            current_index = index
            # Match HEAD
            if HEAD_REGEX.match(line.strip()):
                self.parse_head(lines, current_index)

            # Match INDI
            if INDI_REGEX.match(line.strip()):
                self.parse_indi(lines, current_index)

            # Match FAM
            if FAM_REGEX.match(line.strip()):
                self.parse_fam(lines, current_index)

    def parse_indi(self, lines, start_index):
        matches = INDI_REGEX.match(lines[start_index])
        level = matches.group(1)
        indi_id = matches.group(2)
        indi = Ind(indi_id)
        current_index = start_index

        for index, line in enumerate(lines[start_index + 1:]):
            if line.startswith(level):
                break
            current_index += 1
            current_line = line.strip()

            # FAMS
            matches = FAMS_REGEX.match(current_line)
            if matches:
                indi.fams = matches.group(2)

            # FAMC
            matches = FAMC_REGEX.match(current_line)
            if matches:
                indi.famc = matches.group(2)

            # SEX
            matches = SEX_REGEX.match(current_line)
            if matches:
                if matches.group(2) in ('M', 'F'):
                    indi.sex = matches.group(2)
                else:
                    indi.sex = 'U'

            # NAME
            if NAME_REGEX.match(current_line):
                givn, surn = self.parse_name(lines, current_index)
                indi.given_name = givn
                indi.surname = surn

            # BIRT
            if BIRT_REGEX.match(current_line):
                date, place = self.parse_birt(lines, current_index)
                indi.birth['date'] = date
                indi.birth['place'] = place
                if date:
                    indi.birth['year'] = df.extract_year(date)

            # DEAT
            if DEAT_REGEX.match(current_line):
                date, place = self.parse_deat(lines, current_index)
                indi.death['date'] = date
                indi.death['place'] = place
                if date:
                    indi.death['year'] = df.extract_year(date)

            # DCAUSE
            if DCAUSE_REGEX.match(current_line):
                matches = NOTE_REGEX.match(lines[index + 1].strip())
                if matches:
                    indi.death['cause'] = matches.group(2)

        self.individuals[indi_id] = indi

    @staticmethod
    def parse_name(lines, start_index):
        matches = NAME_REGEX.match(lines[start_index])
        level = matches.group(1)

        givn = ''
        surn = ''

        for index, line in enumerate(lines[start_index + 1:]):
            current_line = line.strip()
            if line.startswith(str(level)) or current_line == '':
                return givn, surn

            # GIVN
            matches = GIVN_REGEX.match(current_line)
            if matches:
                givn = matches.group(2)

            matches = SURN_REGEX.match(current_line)
            if matches:
                surn = matches.group(2)

    @staticmethod
    def parse_birt(lines, start_index):
        matches = BIRT_REGEX.match(lines[start_index])
        level = matches.group(1)

        date = None
        place = None

        for index, line in enumerate(lines[start_index + 1:]):
            current_line = line.strip()
            if line.startswith(str(level)) or current_line == '':
                return date, place
            matches = DATE_REGEX.match(current_line)
            if matches:
                date = matches.group(2)

            matches = PLAC_REGEX.match(current_line)
            if matches:
                place = matches.group(2)

    @staticmethod
    def parse_deat(lines, start_index):
        matches = DEAT_REGEX.match(lines[start_index])
        level = matches.group(1)

        date = None
        place = None

        for index, line in enumerate(lines[start_index + 1:]):
            current_line = line.strip()
            if line.startswith(str(level)) or current_line == '':
                return date, place
            matches = DATE_REGEX.match(current_line)
            if matches:
                date = matches.group(2)

            matches = PLAC_REGEX.match(current_line)
            if matches:
                place = matches.group(2)

    def parse_head(self, lines, start_index):
        level = 0
        for index, line in enumerate(lines[start_index + 1:]):
            current_line = line.strip()
            if line.startswith(str(level)):
                break
            matches = TREE_REGEX.match(current_line)
            if matches:
                self.name = matches.group(2)

    def parse_fam(self, lines, start_index):
        matches = FAM_REGEX.match(lines[start_index])
        level = matches.group(1)
        fam_id = matches.group(2)
        family = FamilyGC(fam_id)
        current_index = start_index

        for index, line in enumerate(lines[start_index + 1:]):
            if line.startswith(level):
                break
            current_index += 1
            current_line = line.strip()

            # HUSB
            matches = HUSB_REGEX.match(current_line)
            if matches:
                family.husband = matches.group(2)

            # WIFE
            matches = WIFE_REGEX.match(current_line)
            if matches:
                family.wife = matches.group(2)

            # CHIL
            matches = CHIL_REGEX.match(current_line)
            if matches:
                family.children.append(matches.group(2))

            # MARR
            if MARR_REGEX.match(current_line):
                date, place = self.parse_marr(lines, current_index)
                family.marriage['date'] = date
                family.marriage['place'] = place

            # DIV
            if DIV_REGEX.match(current_line):
                date, place = self.parse_div(lines, current_index)
                family.divorce['date'] = date
                family.divorce['place'] = place

        self.families[fam_id] = family

    @staticmethod
    def parse_marr(lines, start_index):
        matches = MARR_REGEX.match(lines[start_index])
        level = matches.group(1)

        date = None
        place = None

        for index, line in enumerate(lines[start_index + 1:]):
            current_line = line.strip()
            if line.startswith(str(level)) or current_line == '':
                return date, place
            matches = DATE_REGEX.match(current_line)
            if matches:
                date = matches.group(2)

            matches = PLAC_REGEX.match(current_line)
            if matches:
                place = matches.group(2)

        return date, place

    @staticmethod
    def parse_div(lines, start_index):
        matches = DIV_REGEX.match(lines[start_index])
        level = matches.group(1)

        date = None
        place = None

        for index, line in enumerate(lines[start_index + 1:]):
            current_line = line.strip()
            if line.startswith(str(level)) or current_line == '':
                return date, place
            matches = DATE_REGEX.match(current_line)
            if matches:
                date = matches.group(2)

            matches = PLAC_REGEX.match(current_line)
            if matches:
                place = matches.group(2)

        return date, place

    def get_tree_name(self):
        return self.name

    def print_individual(self, indi_id):
        if indi_id not in self.individuals.keys():
            print("That person does not exist!")
            return

        indi = self.individuals[indi_id]
        print(f"Namn: {indi.get_name()}")
        if indi.famc not in self.families.keys():
            print("No family information about person!")
            return

        father = self.get_father(indi_id)
        mother = self.get_mother(indi_id)

        print(f"Far: {father.get_name()}")
        print(f"Mor: {mother.get_name()}")

    def get_father(self, indi_id):
        try:
            return self.individuals[self.families[self.individuals[indi_id].famc].husband]
        except KeyError:
            return None

    def get_mother(self, indi_id):
        try:
            return self.individuals[self.families[self.individuals[indi_id].famc].wife]
        except KeyError:
            return None

    def get_individual(self, indi_id):
        try:
            return self.individuals[indi_id]
        except KeyError:
            return None

    def check_duplicates(self, indi_id=None):
        duplicates = {}
        already_checked = []
        if indi_id:
            duplicates[indi_id] = []
        else:
            for target_id, target_props in self.individuals.items():
                temp_duplicates = []
                for match_id, match_props in self.individuals.items():
                    if self.individuals[target_id].get_name() == self.individuals[match_id].get_name() and \
                       self.individuals[target_id].get_birth_date() == self.individuals[match_id].get_birth_date() and \
                       self.individuals[target_id].get_birth_place() == self.individuals[match_id].get_birth_place() \
                       and match_id != target_id and match_id not in already_checked:
                        temp_duplicates.append(match_id)
                if temp_duplicates:
                    duplicates[target_id] = temp_duplicates.copy()

                already_checked.append(target_id)

        return duplicates


def main():
    tree = Gedcom(GEDFILE)

    duplicates = tree.check_duplicates()
    if len(duplicates) > 0:
        print("The following people might be duplicates:")
        for target, match in duplicates.items():
            print("Name: " + tree.individuals[target].get_name())
            print("Birth date: " + tree.individuals[target].get_birth_date())
            print("Birth place: " + tree.individuals[target].get_birth_place())
            print("\n")

    else:
        print("No potential duplicates found!")

def clear_db():
    Individual.objects.all().delete()

def handle_uploaded_file(tree):
    gedcom_tree = Gedcom(tree.gedcom_file.path)
    tree.save()

    # List of Individual entries to bulk add to DB
    individuals = []
    families = []
    children = []

    for id, props in gedcom_tree.individuals.items():
        ind = Individual()
        ind.indi_id = id
        ind.tree = tree
        ind.first_name = props.given_name
        ind.last_name = props.surname
        ind.sex = props.sex
        ind.birth_date = props.birth['date']
        ind.birth_place = props.birth['place']
        ind.birth_year = props.birth['year']
        ind.death_date = props.death['date']
        ind.death_place = props.death['place']
        ind.death_cause = props.death['cause']
        ind.death_year = props.death['year']

        individuals.append(ind)

    # Bulk add objects to improve performance
    Individual.objects.bulk_create(individuals)

    for id, props in gedcom_tree.families.items():
        fam = Family()
        fam.tree = tree
        fam.family_id = id
        if props.husband:
            husband = Individual.objects.get(tree=tree, indi_id=props.husband)
            fam.husband = husband
        if props.wife:
            wife = Individual.objects.get(tree=tree, indi_id=props.wife)
            fam.wife = wife
        if props.marriage['date']:
            fam.marriage_date = props.marriage['date']
        if props.marriage['place']:
            fam.marriage_place = props.marriage['place']
        if props.divorce['date']:
            fam.divorce_date = props.divorce['date']
        if props.divorce['place']:
            fam.divorce_place = props.divorce['place']
        for c in props.children:
            child = Child()
            child.family = fam
            child_indi = Individual.objects.get(tree=tree, indi_id=c)
            child.indi = child_indi
            children.append(child)

        families.append(fam)

    Family.objects.bulk_create(families)
    Child.objects.bulk_create(children)