def has_group(user, *group_names):
    if not user.is_authenticated:
        return False
    return user.groups.filter(name__in=list(group_names)).exists()
