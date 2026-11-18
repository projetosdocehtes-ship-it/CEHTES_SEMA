from django import template

register = template.Library()


@register.filter(name="addattrs")
def addattrs(field, css):
    attrs = {}
    definition = css.split(",")

    for d in definition:
        if "=" in d:
            key, value = d.split("=")
            attrs[key] = value

    return field.as_widget(attrs=attrs)
