from .BaseDataModel import BaseDataModel
from .db_schemes import DataChunk
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from pymongo import InsertOne
from fastapi.responses import JSONResponse

class ChunkModel(BaseDataModel):
    
    def __init__(self, db_client):
        super().__init__(db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_CHUNK_NAME.value]

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
        return instance  

    async def init_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.COLLECTION_CHUNK_NAME.value not in all_collections:
            self.collection = self.db_client[DataBaseEnum.COLLECTION_CHUNK_NAME.value]
        indexes = DataChunk.get_indexes()
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


    async def create_chunk(self, chunk:DataChunk):
        result = await self.collection.insert_one(chunk.model_dump(by_alias=True, exclude_unset=True))
        chunk._id = result.inserted_id
        return chunk
    
    async def get_chunk(self, chunk_id:str):
        result = self.collection.find_one({
            "_id":ObjectId(chunk_id)
        })

        if result == None :
            return None
        
        return DataChunk(**result)
    
    async def insert_many_chunks(self, chunks:list , batch_size : int=100):
        
        for i in range(0,len(chunks), batch_size):
            batch = chunks[i:i+batch_size]

            operations = [
                InsertOne(document=chunk.model_dump(by_alias=True, exclude_unset=True))
                for chunk in batch
            ]

            await self.collection.bulk_write(operations)

        return len(chunks)
    
    async def delete_chunks_by_project_id(self, project_id: ObjectId):
        print("project_id is : ",project_id) #depugging step 
        result = await self.collection.delete_many({
            "chunk_project_id": project_id
        })

        return result.deleted_count

    

    
    