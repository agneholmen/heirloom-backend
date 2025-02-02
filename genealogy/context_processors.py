from .models import Tree

def tree_data(request):
    trees = Tree.objects.filter(user=request.user).order_by('name')

    return {
        'trees': trees
    }