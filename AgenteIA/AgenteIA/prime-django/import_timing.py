# import importlib
# import importlib.abc
# import importlib.util
# import sys
# import time

# log_file = "import_timing.log"


# class ImportTimerFinder(importlib.abc.MetaPathFinder):
#     def find_spec(self, fullname, path, target=None):
#         start_time = time.time()
#         try:
#             spec = importlib.util.find_spec(fullname, path)
#         except Exception:
#             spec = None
#         end_time = time.time()
#         duration = end_time - start_time

#         # Verifica se o módulo faz parte do seu projeto ou que você pode manipular
#         if duration > 0.001:
#             with open(log_file, "a") as f:
#                 f.write(f"Time to find spec for {fullname}: {duration:.4f} seconds\n")

#         return spec


# class ImportTimerLoader(importlib.abc.Loader):
#     def create_module(self, spec):
#         return None  # Usa o padrão do importlib

#     def exec_module(self, module):
#         start_time = time.time()
#         try:
#             importlib.import_module(module.__name__)
#         except Exception:
#             pass
#         end_time = time.time()
#         duration = end_time - start_time

#         # Verifica se o módulo faz parte do seu projeto ou que você pode manipular
#         if duration > 0.001 and ("apps.home" in module.__name__ in module.__name__):
#             with open(log_file, "a") as f:
#                 f.write(f"Time to import {module.__name__}: {duration:.4f} seconds\n")


# # Adiciona o finder personalizado ao início da lista de finders
# sys.meta_path.insert(0, ImportTimerFinder())
