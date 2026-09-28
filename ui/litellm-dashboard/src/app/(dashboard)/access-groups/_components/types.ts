export interface AccessGroup {
  id: string;
  name: string;
  description: string;
  modelIds: string[];
  listedModelNames: string[];
  mcpServerIds: string[];
  agentIds: string[];
  keyIds: string[];
  teamIds: string[];
  createdAt: string;
  createdBy: string;
  updatedAt: string;
  updatedBy: string;
}
