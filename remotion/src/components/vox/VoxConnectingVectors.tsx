import React from "react";
import { VoxConnectionItem } from "./VoxCompositeStage";
import { RedString, RedStringConnection } from "./RedString";

export const VoxConnectingVectors: React.FC<{
  connections?: (VoxConnectionItem & { dashed?: boolean; uncertain?: boolean })[];
  width?: number;
  height?: number;
}> = ({ connections = [], width = 1920, height = 1080 }) => {
  return (
    <RedString
      connections={connections as RedStringConnection[]}
      width={width}
      height={height}
    />
  );
};
