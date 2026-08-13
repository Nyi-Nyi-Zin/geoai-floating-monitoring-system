export type LayerVisibility = {
  floodRisk: boolean;
  gridCells: boolean;
  buildings: boolean;
  currentWater: boolean;
  historicalFlood: boolean;
  hand: boolean;
  rivers: boolean;
  canals: boolean;
  roads: boolean;
  boundary: boolean;
  sensors: boolean;
  labels: boolean;
};

export type BasemapMode = "satellite" | "terrain";

export type FloodMonitoringMapHandle = {
  zoomIn: () => void;
  zoomOut: () => void;
  locate: () => void;
  resetView: () => void;
};
