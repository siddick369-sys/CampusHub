from django import template

register = template.Library()


@register.simple_tag
def unread_notifications_count(user):
    """
    Retourne le nombre de notifications non lues pour un utilisateur donné.
    Utilisation dans les templates :
      {% unread_notifications_count user as notif_count %}
    """
    if user.is_authenticated:
        return user.notifications.filter(is_read=False).count()
    return 0