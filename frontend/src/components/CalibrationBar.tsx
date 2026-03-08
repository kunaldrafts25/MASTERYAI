import { CalibrationData } from "@/lib/hooks/useSessionState";
import { CALIBRATION } from "@/lib/constants";

interface CalibrationBarProps {
  calibration: CalibrationData;
}

export default function CalibrationBar({ calibration }: CalibrationBarProps) {
  return (
    <div className="max-w-chat mx-auto w-full px-4 py-1.5 flex flex-wrap gap-4 md:gap-6 text-xs">
      <span className="text-zinc-500">
        Confidence:{" "}
        <span className="text-zinc-300">
          {(calibration.self_assessment * 100).toFixed(0)}%
        </span>
      </span>
      <span className="text-zinc-500">
        Actual:{" "}
        <span className="text-zinc-300">
          {(calibration.actual_score * 100).toFixed(0)}%
        </span>
      </span>
      <span
        className={
          Math.abs(calibration.gap) > CALIBRATION.GAP_ALERT ? "text-red-400" : "text-green-400"
        }
      >
        Gap: {(calibration.gap * 100).toFixed(0)}%
      </span>
    </div>
  );
}
