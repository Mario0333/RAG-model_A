from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from .enums import DataBaseEnum

class ProjectModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.VALUE]

    async def create_project(self, project : Project):
        result = await self.collection.insert_one(project.model_dump())
        project._id = result.inserted_id
        return project
    
    async def get_project_or_create_one(self, project_id:str):
        record = await self.collection.find_one({
                                                    "project_id":project_id
                                                 })
        
        if record is None :
            #create new project
            project = Project(project_id=project_id)
            project = await self.create_project(project=project)

            return project
        
        return Project(**record)

    async def get_all_projects(self, page: int = 1, page_size: int = 10):
        # page represents the current page you want to retrieve.
        # page_size represents the number of documents you want per page.
        
        # Count total number of documents
        total_documents = await self.collection.count_documents({})
        
        # Calculate the total number of pages
        total_pages = total_documents // page_size
        if total_documents % page_size > 0:
            total_pages += 1

        # Create a cursor with skip and limit for pagination
        cursor = self.collection.find().skip((page - 1) * page_size).limit(page_size)
        # Explanation of the code:
        # .find() queries all documents in the collection.
        # .skip() skips a calculated number of documents based on the page number.
        # .limit() restricts the number of documents returned to the page size.
        # Using cursor is memory-efficient, as it allows MongoDB to fetch results in batches.

        documents = list(cursor)

        projects=[]
        async for doc in cursor:
            projects.append(Project(**doc))

        return projects, total_pages 
    
    
