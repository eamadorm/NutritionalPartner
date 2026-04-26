# SMAE Extraction Engine
 
 This module handles the ingestion and extraction of nutritional data from SMAE PDFs.
 
 ## Pipeline Architecture
 
 ```mermaid
 graph TD
     subgraph Input
         A[PDF Document] --> B[GCS Bucket]
         B --> C[ExtractionRequest]
     end
 
     subgraph "IngestionPipeline (Orchestrator)"
         C --> D[1. extract_parallel]
         D --> E[Gemini Flash Batch Processing]
         E --> F[2. transform]
         F --> G[FoodItem Models / UUID5 Enrichment]
         G --> H[3. verify]
         H --> I[4. load]
     end
 
     subgraph Output
         I --> J[SCD Type 2: Mark Previous Inactive]
         J --> K[Bulk Load to BigQuery]
         K --> L[ExtractionResponse]
         K --> M[Dead-Letter Table Routing]
     end
```
 
 ## Quick Start
 
 ### Sandbox Setup
 1. Create resources: `./source_code/create_resources.sh`
 2. Verify extraction: Run `smae_extraction_verify.ipynb`
 
 ### Usage
 ```python
 from backend.smae_engine.source_code.main import IngestionPipeline
 from backend.smae_engine.source_code.schemas import ExtractionRequest
 
 pipeline = IngestionPipeline()
 request = ExtractionRequest(gcs_uri="gs://your-bucket/file.pdf")
 response = pipeline.run(request)
 ```
 
 For detailed documentation, see [smae_engine.md](../../docs/modules/smae_engine.md).
