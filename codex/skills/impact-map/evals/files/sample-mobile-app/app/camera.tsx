import { CameraControls } from "../src/components/CameraControls";

export default function CameraScreen() {
  return <CameraControls minZoom={1} maxZoom={5} />;
}
