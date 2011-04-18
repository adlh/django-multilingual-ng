from multilingual.languages import get_language, FALLBACK_FIELD_SUFFIX
from multilingual.utils import GLL


def log_does_not_exist(parent, translation_name):
    #print "TRANSLATION DOES NOT EXIST", type(parent), parent.pk, translation_name
    pass
    # TODO: use django log if available
    #from  django.utils.log import debug
    #debug('some message')


class TranslationProxyField(object):
    """
    Provides an access to translated fields
    Based on GenericForeignKey field
    """
    def __init__(self, field_name, language_code, fallback=False):
        self._field_name = field_name
        self._language_code = language_code
        self._fallback = fallback
        self.name = field_name
        if language_code:
            self.name += '_' + self.language_code.replace('-', '_')
        if fallback:
            self.name += FALLBACK_FIELD_SUFFIX

    def contribute_to_class(self, cls, name):
        if self.name != name:
            raise ValueError('Field proxy %s is added to class under bad attribute name.' % self)
        self.model = cls
        self.cache_attr = "_%s_cache" % name
        cls._meta.add_virtual_field(self)

        #===============================================================================================================
        # # For some reason I don't totally understand, using weakrefs here doesn't work.
        # signals.pre_init.connect(self.instance_pre_init, sender=cls, weak=False)
        #===============================================================================================================

        # Connect myself as the descriptor for this field
        setattr(cls, name, self)

    # This might be used to create multilingual model instance with translations in __init__ args
    # Example: SomeMultilingualModel(trans_field_en='some', trans_field_cs='neco')
    #===================================================================================================================
    # def instance_pre_init(self, signal, sender, args, kwargs, **_kwargs):
    #    """
    #    Handles initializing an object with the generic FK instaed of
    #    content-type/object-id fields.
    #    """
    #    if self.name in kwargs:
    #        value = kwargs.pop(self.name)
    #        kwargs[self.ct_field] = self.get_content_type(obj=value)
    #        kwargs[self.fk_field] = value._get_pk_val()
    #===================================================================================================================

    @property
    def language_code(self):
        """
        If _language_code is None we are the _current field, so we use the
        currently used language for lookups.
        """
        if self._language_code:
            return self._language_code

        #TODO: this all should be part of some 'languages' function
        if GLL.is_active:
            return GLL.language_code

        # This call is quite problematic when you are using commands, because django by default activates 'en-us' 
        # even though it is not in your settings.LANGUAGES. In which case ValueError at line 56 is raised.
        # For further details see Ticket #13859 http://code.djangoproject.com/ticket/13859
        # Language 'en-us' is set in django/core/management/base.py:202-209 in BaseCommand.execute()

        return get_language()

    @property
    def fallback(self):
        if not self._language_code and GLL.is_active:
            return False
        return self._fallback

    def __get__(self, instance, instance_type=None):
        """
        Returns field translation or None
        """
        if instance is None:
            return self

        try:
            return getattr(
                instance._get_translation(self.language_code, fallback=self.fallback),
                self._field_name
            )
        except instance._meta.translation_model.DoesNotExist:
            log_does_not_exist(instance, self.name)
            return None

    def __set__(self, instance, value):
        """
        Sets field translation
        """
        if instance is None:
            raise AttributeError(u"%s must be accessed via instance" % self.name)

        translation = instance._get_translation(
            self.language_code,
            can_create=True
        )
        setattr(translation, self._field_name, value)
