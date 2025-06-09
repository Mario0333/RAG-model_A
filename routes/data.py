from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import os
from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController, ErrorController, ProcessController  # Import correctly
import aiofiles
from models import ResponseSignal
import logging
from routes.schemes import ProcessRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.db_schemes.data_chunk import DataChunk
from models.db_schemes import Asset
from models.enums.AssetTypeEnum import AssetTypeEnum
from bson import ObjectId

logger = logging.getLogger('uvicorn.error')

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"]
)

@data_router.post("/upload/{project_id}")
async def upload_data(request:Request ,project_id: str, file: UploadFile, app_settings: Settings = Depends(get_settings)):
    
    project_model =await ProjectModel.create_instance(db_client=request.app.db_client)

    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    # Validate the file properties
    is_valid, result_signal = DataController().validate_uploaded_file(file)
    
    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal":result_signal
            }
        )

    project_dir_path = ProjectController().get_project_path(project_id)
    file_path, file_id = DataController().generate_unique_filepath(
        orig_file_name=file.filename,
        project_id=project_id
    )

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(size=app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)
    except Exception as e:
        logger.error(f"Error while uploading file: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal":ResponseSignal.FILE_UPLOAD_FAILED.value
            }
        )

    #store the assetes in the database
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset_resource = Asset(
        asset_project_id=project.id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=file_id,
        asset_size= os.path.getsize(file_path)
    )

    asset_record= await asset_model.create_asset(asset=asset_resource)

    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal":ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                "file_id":str(asset_record.id),
                "project_id": str(project.id)
            }
        )

@data_router.post("/process/{project_id}")
async def process_endpoint(request : Request,project_id: str, process_request:ProcessRequest):
    # file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlab_size = process_request.overlap_size
    do_reset = process_request.do_reset

    """
    #check if the project not in assets
    if not ErrorController().project_found(project_id):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal":ResponseSignal.PROCESSING_PROJECT_NOT_FOUND.value
            }
        )
        """
    
    #check if the file not in project dir 
    # if not ErrorController().file_found(project_id,file_id):
    #     return JSONResponse(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         content={
    #             "signal":ResponseSignal.PROCESSING_FILE_NOT_FOUND.value
    #         }
    #     )    
    
    
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )
    asset_model = await AssetModel.create_instance(
        db_client=request.app.db_client)


    project_file_ids = {}
    if process_request.file_id is not None:
        asset_record = await asset_model.get_asset_record(
            asset_project_id=project.id,
            asset_name=process_request.file_id
        )
        if asset_record is None :
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal":ResponseSignal.FILE_ID_ERROR.value
            }
        )

        project_file_ids ={
            asset_record.id : asset_record.asset_name
        }

    else:
        project_files = await asset_model.get_all_project_assets(
            asset_project_id=project.id,
            asset_type=AssetTypeEnum.FILE.value
        )

        
        project_file_ids = {
            record.id : record.asset_name
            for record in project_files
        }
        
    if len(project_file_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal":ResponseSignal.PROCESSING_FILE_NOT_FOUND.value
            }
        )
    
    #start Processing
    processcontroller = ProcessController(project_id= project_id)



    if do_reset == 1:
        print("deleting . . .") #depugging step
        _ = await chunk_model.delete_chunks_by_project_id(project_id=project.id)

    no_records = 0
    no_files = 0

    for asset_id, file_id in project_file_ids.items():
        file_content = processcontroller.get_file_content(file_id=file_id)

        if file_content is None:
            logger.error(f"Error while processing file: {file_id}")
            continue

        file_chunks = processcontroller.process_file_content(
            file_content=file_content,
            file_id=file_id,
            chunk_size=process_request.chunk_size,
            overlap_size=process_request.overlap_size
        )

        if file_chunks is None or len(file_chunks) == 0 :
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal":ResponseSignal.PROCESSING_FAILED
                }
            )
        
        file_chunks_records = [
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=i+1,
                chunk_project_id=project.id,
                chunk_asset_id=asset_id
            )
            for i, chunk in enumerate(file_chunks)
        ]


        no_records += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
        no_files += 1

    return JSONResponse(
        content={
            "signal": ResponseSignal.PROCESSING_SUCCEDED.value,
            "inserted_chunks": no_records,
            "processed_files": no_files
        }
    )
