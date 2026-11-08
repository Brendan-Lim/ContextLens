import {useRoute} from './useRoute';
import {WorkspaceShell} from '../layout/WorkspaceShell';
import {ProjectWorkspace} from '../features/projects/ProjectWorkspace';
import {TeamWorkspace} from '../features/team/TeamWorkspace';
import {SettingsWorkspace} from '../features/settings/SettingsWorkspace';
import {ReportsWorkspace} from '../features/reports/ReportsWorkspace';
export function App(){const route=useRoute();return <WorkspaceShell route={route}>{route==='/team'?<TeamWorkspace/>:route==='/settings'?<SettingsWorkspace/>:route==='/reports'?<ReportsWorkspace/>:<ProjectWorkspace/>}</WorkspaceShell>;}
