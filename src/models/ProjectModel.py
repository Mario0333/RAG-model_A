from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from .enums.DataBaseEnum import DataBaseEnum

class ProjectModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]

    @classmethod
    async def create_instance(cls, db_client: object):
        """
        why ??! 
        __init__() can't be async function 
        init_collection() must be async function 
        you can't call async function inside onther function without making the caller async 
        so we make an async class function to do both to solve this issue .
        """
        instance = cls(db_client)
        await instance.init_collection()
        print("instance created succefully !!")
        return instance  
      

    async def init_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.COLLECTION_PROJECT_NAME.value not in all_collections:
            self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]
        indexes = Project.get_indexes()
        for index in indexes:
            try:
                print(f"Creating index: {index['name']}")
                await self.collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"]
                )
            except Exception as e:
                print(f"Error creating index {index['name']}: {e}")

    async def create_project(self, project : Project):
        # Insert into MongoDB
        data=project.model_dump(by_alias=True, exclude_unset=True)
        print("Data to insert:",data )
        result = await self.collection.insert_one(data)
        print(result)
        # Set the auto-generated `_id` back to the Pydantic model
        project.id = result.inserted_id
        return project
    
    async def get_project_or_create_one(self, project_id: str):
        print("Looking for project_id:", project_id)  # Debugging step
        record = await self.collection.find_one({
            "project_id": project_id
        })
        print("Record found:", record)  # Debugging step

        if record is None:
            # create new project
            project = Project(project_id=project_id)
            print("Created new Project object:", project.model_dump(by_alias=True))  # Debugging step
            project = await self.create_project(project=project)
            print("Inserted Project into DB:", project.model_dump(by_alias=True))  # Debugging step
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
        cursor = self.collection.find().skip( (page-1) * page_size ).limit(page_size)
        # Explanation of the code:
        # .find() queries all documents in the collection.
        # .skip() skips a calculated number of documents based on the page number.
        # .limit() restricts the number of documents returned to the page size.
        # Using cursor is memory-efficient, as it allows MongoDB to fetch results in batches.

        # documents = list(cursor)

        projects = []
        async for document in cursor:
            projects.append(
                Project(**document)
            )

        return projects, total_pages
    
    
