type CameraControlsProps = {
  minZoom: number;
  maxZoom: number;
};

export function CameraControls({ minZoom, maxZoom }: CameraControlsProps) {
  return (
    <button aria-label="Zoom camera">
      Zoom {minZoom}x-{maxZoom}x
    </button>
  );
}
