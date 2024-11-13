from .BaseController import BaseController
import os

class ErrorController(BaseController):
    def __init__(self):
        super().__init__()

    def project_found(self, project_id: str):
        project_path = os.path.join(self.file_dir,project_id)
        if os.path.exists(project_path):
            return True 

    def file_found(self, project_id: str, file_id: str):
        file_path = os.path.join(self.file_dir,project_id,file_id)
        if os.path.exists(file_path):
            return True 