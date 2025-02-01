from django.templatetags.static import static

def get_default_image(sex):
    if sex == 'M':
        return static('images/male.png')
    elif sex == 'F':
        return static('images/female.png')
    else:
        return static('images/unknown.png')