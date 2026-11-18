# dbrouters.py
import logging

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

class AppRouter:
    """
    A router to control all database operations on models for certain apps.
    """

    app_label_to_db = {
        "selos_sqlserver": "sqlserver_db",  # O app específico que usará o SQL Server
    }

    def db_for_read(self, model, **hints):
        """
        Attempts to read models go to the specific database.
        """
        return self.app_label_to_db.get(model._meta.app_label, "default")

    def db_for_write(self, model, **hints):
        """
        Attempts to write models go to the specific database.
        """
        return self.app_label_to_db.get(model._meta.app_label, "default")

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the app is involved.
        """
        db_obj1 = self.app_label_to_db.get(obj1._meta.app_label, "default")
        db_obj2 = self.app_label_to_db.get(obj2._meta.app_label, "default")
        if db_obj1 and db_obj2:
            return db_obj1 == db_obj2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the app only appears in the specific database.
        """
        if app_label in self.app_label_to_db:
            return db == self.app_label_to_db[app_label]
        return db == "default"
