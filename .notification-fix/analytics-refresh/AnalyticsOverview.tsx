import { MetricGrid } from "./MetricGrid";
import OperationsCharts from "./OperationsCharts";
import type { AnalyticsOverview as AnalyticsOverviewData } from "@/types/analytics";
export function AnalyticsOverview({overview, detailed = false}: {overview:AnalyticsOverviewData; detailed?: boolean}) {
 return <div className="space-y-5"><MetricGrid metrics={overview.metrics}/><OperationsCharts overview={overview} detailed={detailed}/></div>;
}
