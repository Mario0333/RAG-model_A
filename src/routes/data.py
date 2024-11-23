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
from models.db_schemes.data_chunk import DataChunk

logger = logging.getLogger('uvicorn.error')

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"]
)

@data_router.post("/upload/{project_id}")
async def upload_data(request:Request ,project_id: str, file: UploadFile, app_settings: Settings = Depends(get_settings)):
    
    project_model = ProjectModel(db_client=request.app.db_client)

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

    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal":ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                "file_id":file_id,
                "project_id": str(project.id)
            }
        )

@data_router.post("/process/{project_id}")
async def process_endpoint(request : Request,project_id: str, process_request:ProcessRequest):
    file_id = process_request.file_id
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
    if not ErrorController().file_found(project_id,file_id):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal":ResponseSignal.PROCESSING_FILE_NOT_FOUND.value
            }
        )    
    
    
    project_model = ProjectModel(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )
    
    #start Processing
    processcontroller = ProcessController(project_id= project_id)

    file_content = processcontroller.get_file_content(file_id=file_id)
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
        )
        for i, chunk in enumerate(file_chunks)
    ]

    chunk_model = ChunkModel(
        db_client=request.app.db_client
    )

    no_records = await chunk_model.insert_many_chunks(chunks=file_chunks_records)

    return JSONResponse(
        content={
            "signal": ResponseSignal.PROCESSING_SUCCEDED.value,
            "inserted_chunks": no_records
        }
    )

