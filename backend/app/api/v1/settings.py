"""
Settings API Endpoints
Endpoints for application configuration and settings.

Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import csv
import io

from app.api.deps import get_db_dependency, get_current_user
from app.db.models.setting import Setting
from app.db.models.species import Species
from app.db.models.station import Station
from app.db.models.detection import Detection
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class SettingResponse(BaseModel):
    """Setting response model."""
    key: str
    value: Optional[str]
    data_type: Optional[str]
    description: Optional[str]


class SettingUpdate(BaseModel):
    """Setting update model."""
    value: str
    data_type: Optional[str] = "str"
    description: Optional[str] = None


class TaxonomyUploadResponse(BaseModel):
    """Response model for taxonomy upload."""
    success: bool
    species_updated: int
    species_created: int
    families_added: int
    total_ebird_species: int
    message: str


class DetectionUploadResponse(BaseModel):
    """Response model for detection CSV upload."""
    success: bool
    detections_added: int
    detections_skipped: int
    species_created: int
    stations_matched: int
    message: str


@router.get("/", response_model=List[SettingResponse])
async def get_all_settings(db: Session = Depends(get_db_dependency)):
    """
    Get all application settings.
    """
    settings = db.query(Setting).all()
    return [SettingResponse(
        key=s.key,
        value=s.value,
        data_type=s.data_type,
        description=s.description
    ) for s in settings]


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: Session = Depends(get_db_dependency)):
    """
    Get a specific setting by key.
    """
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    return SettingResponse(
        key=setting.key,
        value=setting.value,
        data_type=setting.data_type,
        description=setting.description
    )


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    setting_data: SettingUpdate,
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
):
    """
    Update or create a setting.
    """
    setting = db.query(Setting).filter(Setting.key == key).first()

    if setting:
        setting.value = setting_data.value
        if setting_data.data_type:
            setting.data_type = setting_data.data_type
        if setting_data.description:
            setting.description = setting_data.description
    else:
        setting = Setting(
            key=key,
            value=setting_data.value,
            data_type=setting_data.data_type or "str",
            description=setting_data.description
        )
        db.add(setting)

    db.commit()
    db.refresh(setting)

    return SettingResponse(
        key=setting.key,
        value=setting.value,
        data_type=setting.data_type,
        description=setting.description
    )


@router.delete("/{key}")
async def delete_setting(
    key: str,
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a setting.
    """
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    db.delete(setting)
    db.commit()

    return {"success": True, "message": f"Setting '{key}' deleted"}


@router.post("/ebird-taxonomy", response_model=TaxonomyUploadResponse)
async def upload_ebird_taxonomy(
    file: UploadFile = File(...),
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload eBird taxonomy CSV to populate species codes.

    The CSV should contain at minimum:
    - SPECIES_CODE or SPECIES_CD: The 4-6 character eBird species code
    - SCI_NAME or SCIENTIFIC_NAME: The scientific name to match against

    Optional columns:
    - PRIMARY_COM_NAME or COMMON_NAME: Common name
    - ORDER1 or ORDER_NAME: Taxonomic order
    - FAMILY or FAMILY_NAME: Taxonomic family
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        content = await file.read()
        # Try different encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=400, detail="Unable to decode CSV file")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(text_content))

        # Normalize column names (handle different eBird CSV formats)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise HTTPException(status_code=400, detail="CSV has no headers")

        # Map possible column names
        col_map = {}
        for field in fieldnames:
            field_upper = field.upper().strip()
            if field_upper in ['SPECIES_CODE', 'SPECIES_CD', 'SPECIESCODE']:
                col_map['species_code'] = field
            elif field_upper in ['SCI_NAME', 'SCIENTIFIC_NAME', 'SCINAME']:
                col_map['scientific_name'] = field
            elif field_upper in ['PRIMARY_COM_NAME', 'COMMON_NAME', 'COMNAME']:
                col_map['common_name'] = field
            elif field_upper in ['ORDER1', 'ORDER_NAME', 'ORDER']:
                col_map['order'] = field
            elif field_upper in ['FAMILY', 'FAMILY_NAME']:
                col_map['family'] = field

        if 'species_code' not in col_map or 'scientific_name' not in col_map:
            raise HTTPException(
                status_code=400,
                detail="CSV must contain SPECIES_CODE and SCI_NAME columns"
            )

        updated_count = 0
        created_count = 0
        families_added = 0
        total_rows = 0
        families_seen = set()

        for row in reader:
            species_code = row.get(col_map['species_code'], '').strip()
            scientific_name = row.get(col_map['scientific_name'], '').strip()

            if not species_code or not scientific_name:
                continue

            total_rows += 1

            # Get optional fields
            common_name = row.get(col_map.get('common_name', ''), '').strip() if 'common_name' in col_map else ''
            family = row.get(col_map.get('family', ''), '').strip() if 'family' in col_map else ''
            order = row.get(col_map.get('order', ''), '').strip() if 'order' in col_map else ''

            # Track unique families
            if family:
                families_seen.add(family)

            # Find species by scientific name
            species = db.query(Species).filter(
                Species.scientific_name.ilike(scientific_name)
            ).first()

            if species:
                # Update existing species - always update from eBird data
                species.ebird_code = species_code

                # Track if we're adding a new family
                if family and not species.family:
                    families_added += 1

                # Always update family and order from eBird
                if family:
                    species.family = family
                if order:
                    species.order = order
                if common_name and not species.common_name:
                    species.common_name = common_name

                updated_count += 1
            else:
                # Create new species from eBird taxonomy
                new_species = Species(
                    scientific_name=scientific_name,
                    common_name=common_name or scientific_name,
                    species_id=None,  # No BirdWeather ID
                    ebird_code=species_code,
                    family=family or None,
                    order=order or None
                )
                db.add(new_species)
                created_count += 1
                if family:
                    families_added += 1

            # Commit periodically to avoid memory issues
            if (updated_count + created_count) % 1000 == 0:
                db.commit()

        db.commit()

        # Update taxonomy stats setting
        stats_setting = db.query(Setting).filter(Setting.key == 'ebird_taxonomy_stats').first()
        import json
        from datetime import datetime
        stats = {
            'last_updated': datetime.utcnow().isoformat(),
            'species_with_codes': db.query(Species).filter(Species.ebird_code.isnot(None)).count(),
            'species_with_families': db.query(Species).filter(Species.family.isnot(None)).count(),
            'total_species': db.query(Species).count(),
            'unique_families': len(families_seen),
            'ebird_entries': total_rows
        }

        if stats_setting:
            stats_setting.value = json.dumps(stats)
            stats_setting.data_type = 'json'
        else:
            db.add(Setting(
                key='ebird_taxonomy_stats',
                value=json.dumps(stats),
                data_type='json',
                description='eBird taxonomy import statistics'
            ))
        db.commit()

        return TaxonomyUploadResponse(
            success=True,
            species_updated=updated_count,
            species_created=created_count,
            families_added=families_added,
            total_ebird_species=total_rows,
            message=f"Processed {total_rows} eBird species. Updated {updated_count} existing, created {created_count} new. {families_added} species now have family data. Found {len(families_seen)} unique families."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


@router.get("/ebird-taxonomy/stats")
async def get_taxonomy_stats(db: Session = Depends(get_db_dependency)):
    """
    Get eBird taxonomy statistics.
    """
    import json

    stats_setting = db.query(Setting).filter(Setting.key == 'ebird_taxonomy_stats').first()

    species_with_codes = db.query(Species).filter(Species.ebird_code.isnot(None)).count()
    species_with_families = db.query(Species).filter(Species.family.isnot(None)).count()
    total_species = db.query(Species).count()

    # Get stored stats for additional fields
    stored_stats = {}
    if stats_setting:
        try:
            stored_stats = json.loads(stats_setting.value)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        'species_with_codes': species_with_codes,
        'species_with_families': species_with_families,
        'total_species': total_species,
        'coverage_percent': round(species_with_codes / total_species * 100, 1) if total_species > 0 else 0,
        'unique_families': stored_stats.get('unique_families', 0),
        'ebird_entries': stored_stats.get('ebird_entries', 0),
        'last_updated': stored_stats.get('last_updated')
    }


@router.post("/detections/upload", response_model=DetectionUploadResponse)
async def upload_detections_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload detection data from CSV file.

    Expected CSV columns:
    - Timestamp: Detection timestamp (e.g., "2025-12-22 19:49:42 -0500")
    - Common Name: Bird common name
    - Scientific Name: Bird scientific name
    - Latitude: Detection latitude
    - Longitude: Detection longitude
    - Station: Station name to match against existing stations
    - Confidence: Detection confidence (0-1)
    - Score: Detection score (optional)
    - Probability: Detection probability (optional)
    - Soundscape: URL to soundscape audio (optional)
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        content = await file.read()
        # Try different encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=400, detail="Unable to decode CSV file")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(text_content))

        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV has no headers")

        # Normalize column names
        col_map = {}
        for field in reader.fieldnames:
            field_lower = field.lower().strip()
            if 'timestamp' in field_lower:
                col_map['timestamp'] = field
            elif field_lower == 'common name':
                col_map['common_name'] = field
            elif field_lower == 'scientific name':
                col_map['scientific_name'] = field
            elif field_lower == 'latitude':
                col_map['latitude'] = field
            elif field_lower == 'longitude':
                col_map['longitude'] = field
            elif field_lower == 'station':
                col_map['station'] = field
            elif field_lower == 'confidence':
                col_map['confidence'] = field
            elif field_lower == 'score':
                col_map['score'] = field
            elif field_lower == 'soundscape':
                col_map['soundscape'] = field

        required = ['timestamp', 'scientific_name', 'station']
        missing = [r for r in required if r not in col_map]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"CSV missing required columns: {', '.join(missing)}"
            )

        # Cache for stations and species
        station_cache = {}
        species_cache = {}

        detections_added = 0
        detections_skipped = 0
        species_created = 0
        stations_matched = set()

        for row in reader:
            try:
                # Parse timestamp
                timestamp_str = row.get(col_map['timestamp'], '').strip()
                if not timestamp_str:
                    detections_skipped += 1
                    continue

                # Parse various timestamp formats
                timestamp = None
                for fmt in [
                    '%Y-%m-%d %H:%M:%S %z',  # 2025-12-22 19:49:42 -0500
                    '%Y-%m-%d %H:%M:%S',      # 2025-12-22 19:49:42
                    '%Y-%m-%dT%H:%M:%S%z',    # ISO format
                    '%Y-%m-%dT%H:%M:%S',      # ISO without tz
                ]:
                    try:
                        timestamp = datetime.strptime(timestamp_str, fmt)
                        break
                    except ValueError:
                        continue

                if not timestamp:
                    logger.warning(f"Could not parse timestamp: {timestamp_str}")
                    detections_skipped += 1
                    continue

                # Get station
                station_name = row.get(col_map['station'], '').strip()
                if not station_name:
                    detections_skipped += 1
                    continue

                if station_name not in station_cache:
                    # Match station by name (partial match)
                    station = db.query(Station).filter(
                        Station.name.ilike(f"%{station_name}%")
                    ).first()
                    station_cache[station_name] = station

                station = station_cache[station_name]
                if not station:
                    detections_skipped += 1
                    continue

                stations_matched.add(station.id)

                # Get or create species
                scientific_name = row.get(col_map['scientific_name'], '').strip()
                common_name = row.get(col_map.get('common_name', ''), '').strip() if 'common_name' in col_map else ''

                if not scientific_name:
                    detections_skipped += 1
                    continue

                if scientific_name not in species_cache:
                    species = db.query(Species).filter(
                        Species.scientific_name.ilike(scientific_name)
                    ).first()

                    if not species:
                        # Create new species
                        species = Species(
                            scientific_name=scientific_name,
                            common_name=common_name or scientific_name,
                            species_id=None  # Manual import, no BirdWeather ID
                        )
                        db.add(species)
                        db.flush()
                        species_created += 1

                    species_cache[scientific_name] = species

                species = species_cache[scientific_name]

                # Parse coordinates
                try:
                    latitude = float(row.get(col_map.get('latitude', ''), 0) or 0)
                    longitude = float(row.get(col_map.get('longitude', ''), 0) or 0)
                except (ValueError, TypeError):
                    latitude = station.latitude or 0
                    longitude = station.longitude or 0

                # Parse confidence
                try:
                    confidence = float(row.get(col_map.get('confidence', ''), 0) or 0)
                except (ValueError, TypeError):
                    confidence = 0.0

                # Check for duplicate detection (same station, species, timestamp)
                existing = db.query(Detection).filter(
                    Detection.station_id == station.id,
                    Detection.species_id == species.id,
                    Detection.timestamp == timestamp
                ).first()

                if existing:
                    detections_skipped += 1
                    continue

                # Create detection
                detection = Detection(
                    station_id=station.id,
                    species_id=species.id,
                    detection_id=None,  # Manual upload, no BirdWeather ID
                    timestamp=timestamp,
                    confidence=confidence,
                    latitude=latitude,
                    longitude=longitude,
                    detection_date=timestamp.date(),
                    detection_hour=timestamp.hour
                )
                db.add(detection)
                detections_added += 1

                # Commit periodically to avoid memory issues
                if detections_added % 500 == 0:
                    db.commit()

            except Exception as e:
                logger.warning(f"Error processing row: {e}")
                detections_skipped += 1
                continue

        db.commit()

        return DetectionUploadResponse(
            success=True,
            detections_added=detections_added,
            detections_skipped=detections_skipped,
            species_created=species_created,
            stations_matched=len(stations_matched),
            message=f"Added {detections_added} detections. Skipped {detections_skipped}. Created {species_created} new species. Matched {len(stations_matched)} stations."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading detections: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")
