from django.templatetags.static import static
from easy_thumbnails.files import get_thumbnailer

def get_default_image(sex):
    if sex == 'M':
        return static('images/male.png')
    elif sex == 'F':
        return static('images/female.png')
    else:
        return static('images/unknown.png')
    
def get_profile_photo(person):
    return get_thumbnailer(person.profile_image.image).get_thumbnail({
        'size': (150, 0),
        'crop': 'smart'
    }).url