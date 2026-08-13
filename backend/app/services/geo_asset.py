import math
from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2 import functions as geofunc
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.geo_asset import GeoAsset
from app.schemas.geo_asset import (
    GeoAssetCreate,
    GeoAssetFeature,
    GeoAssetFeatureCollection,
    GeoAssetFeatureProperties,
    GeoAssetImportRequest,
    GeoAssetUpdate,
    PaginationMeta,
)


def _not_found(asset_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "geo_asset_not_found",
            "message": f"GeoAsset '{asset_id}' was not found.",
        },
    )


def _to_feature(asset: GeoAsset) -> GeoAssetFeature:
    geometry = to_shape(asset.geometry)
    return GeoAssetFeature(
        id=asset.id,
        geometry=geometry.__geo_interface__,
        properties=GeoAssetFeatureProperties(
            name=asset.name,
            asset_type=asset.asset_type,
            source_key=asset.source_key,
            description=asset.description,
            metadata=asset.properties,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        ),
    )


class GeoAssetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: GeoAssetCreate) -> GeoAssetFeature:
        asset = GeoAsset(
            name=payload.name,
            asset_type=payload.asset_type,
            source_key=payload.source_key,
            description=payload.description,
            geometry=from_shape(shape(payload.geometry), srid=4326),
            properties=payload.properties,
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return _to_feature(asset)

    def bulk_create(
        self,
        payload: GeoAssetImportRequest,
    ) -> GeoAssetFeatureCollection:
        source_keys = [
            feature.properties.source_key for feature in payload.features
        ]
        if len(source_keys) != len(set(source_keys)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "duplicate_source_key",
                    "message": "Each imported Feature must have a unique source_key.",
                },
            )

        existing_by_key = {
            asset.source_key: asset
            for asset in self.db.scalars(
                select(GeoAsset).where(GeoAsset.source_key.in_(source_keys))
            ).all()
        }
        assets = []
        for feature in payload.features:
            properties = feature.properties
            asset = existing_by_key.get(properties.source_key)
            if asset is None:
                asset = GeoAsset(source_key=properties.source_key)
                self.db.add(asset)
            asset.name = properties.name
            asset.asset_type = properties.asset_type
            asset.description = properties.description
            asset.geometry = from_shape(shape(feature.geometry), srid=4326)
            asset.properties = properties.metadata
            assets.append(asset)

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        for asset in assets:
            self.db.refresh(asset)

        imported = len(assets)
        return GeoAssetFeatureCollection(
            features=[_to_feature(asset) for asset in assets],
            meta=PaginationMeta(
                page=1,
                page_size=imported,
                total=imported,
                pages=1,
            ),
        )

    def get(self, asset_id: UUID) -> GeoAssetFeature:
        asset = self.db.get(GeoAsset, asset_id)
        if asset is None:
            raise _not_found(asset_id)
        return _to_feature(asset)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        asset_type: str | None,
    ) -> GeoAssetFeatureCollection:
        query = select(GeoAsset)
        count_query = select(func.count()).select_from(GeoAsset)
        if asset_type:
            query = query.where(GeoAsset.asset_type == asset_type)
            count_query = count_query.where(GeoAsset.asset_type == asset_type)
        return self._paginate(query, count_query, page=page, page_size=page_size)

    def within_bounds(
        self,
        *,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        page: int,
        page_size: int,
        asset_type: str | None,
    ) -> GeoAssetFeatureCollection:
        if min_lon >= max_lon or min_lat >= max_lat:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "invalid_bounds",
                    "message": "Minimum longitude/latitude must be less than maximum values.",
                },
            )

        envelope = geofunc.ST_MakeEnvelope(
            min_lon,
            min_lat,
            max_lon,
            max_lat,
            4326,
        )
        intersects = geofunc.ST_Intersects(GeoAsset.geometry, envelope)
        query = select(GeoAsset).where(intersects)
        count_query = select(func.count()).select_from(GeoAsset).where(intersects)
        if asset_type:
            query = query.where(GeoAsset.asset_type == asset_type)
            count_query = count_query.where(GeoAsset.asset_type == asset_type)
        return self._paginate(query, count_query, page=page, page_size=page_size)

    def update(
        self,
        asset_id: UUID,
        payload: GeoAssetUpdate,
    ) -> GeoAssetFeature:
        asset = self.db.get(GeoAsset, asset_id)
        if asset is None:
            raise _not_found(asset_id)

        changes = payload.model_dump(exclude_unset=True)
        if "geometry" in changes:
            changes["geometry"] = from_shape(shape(changes["geometry"]), srid=4326)
        for field, value in changes.items():
            setattr(asset, field, value)

        self.db.commit()
        self.db.refresh(asset)
        return _to_feature(asset)

    def delete(self, asset_id: UUID) -> None:
        asset = self.db.get(GeoAsset, asset_id)
        if asset is None:
            raise _not_found(asset_id)
        self.db.delete(asset)
        self.db.commit()

    def _paginate(
        self,
        query: object,
        count_query: object,
        *,
        page: int,
        page_size: int,
    ) -> GeoAssetFeatureCollection:
        total = self.db.scalar(count_query) or 0
        rows = self.db.scalars(
            query.order_by(GeoAsset.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return GeoAssetFeatureCollection(
            features=[_to_feature(asset) for asset in rows],
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                pages=math.ceil(total / page_size) if total else 0,
            ),
        )
