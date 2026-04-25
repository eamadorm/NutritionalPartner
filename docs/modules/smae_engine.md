# SMAE Engine

**Path**: `backend/smae_engine/`

## Overview
The SMAE Engine is responsible for ingesting, processing, and standardizing nutritional data from the *Sistema Mexicano de Alimentos Equivalentes* (SMAE) PDFs. It utilizes Google's Gemini 2.5 Flash via the `google-genai` SDK to perform structured data extraction.

## Architecture
The process follows a two-stage strategy:
1. **Stage 1 (Prototyping)**: Bash scripts manually provision the GCS Bucket (`nutritional-data-sources`). Python scripts extract the PDF blobs, pass them to Vertex AI, and parse the response into structured Pydantic models.
2. **Stage 2 (Deployment)**: (To be implemented) Terraform codification of resources and Cloud Build pipelines.

### Data Flow
1. PDF is uploaded to `gs://nutritional-data-sources/`.
2. `ExtractionRequest` triggers the parsing logic.
3. Gemini Flash extracts the items.
4. Post-processing creates a deterministic `food_uuid` (using `uuid5`) to enforce SCD Type 2 strategies in the database.
5. The `ExtractionResponse` is returned, populated with fully validated `FoodItem` models.

## Schemas
Schemas are heavily typed using `Pydantic` and `Annotated`. All numerical attributes strictly enforce non-negative values. 
- **FoodItem**: Includes 12 columns, notably `food_uuid`, `energy_kcal`, `protein_g`, and `ingested_at`.
- **ExtractionResponse**: Contains the list of `FoodItem`s and metadata concerning the extraction.

## Usage
To execute the backend locally:
```bash
make run-smae-engine
```
To create sandbox resources:
```bash
./backend/smae_engine/source_code/create_resources.sh
```
