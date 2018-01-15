def validation_rule(f):
    f._is_validation_rule = True
    return f
