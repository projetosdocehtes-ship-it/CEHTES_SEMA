# class TenantFileSystemStorage(FileSystemStorage):

#     def __init__(self, *args, **kwargs):
#         if 'location' not in kwargs:
#             # Aqui, presumimos que 'tenant' é uma propriedade global ou contexto que você determinou para sua aplicação multitenant.
#             kwargs['location'] = os.path.join(settings.MEDIA_ROOT, tenant)
#         super().__init__(*args, **kwargs)
