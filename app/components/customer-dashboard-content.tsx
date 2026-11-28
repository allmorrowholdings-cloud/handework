"use client";
import {useInstalledApp} from "./installed-app-mode";
import {AppHomeCard} from "./app-home-card";
import {ServiceDiscovery} from "./service-discovery";
import {CustomerOverview} from "../dashboard/customer-overview";
export function CustomerDashboardContent(){const installed=useInstalledApp();return installed?<AppHomeCard/>:<><ServiceDiscovery/><CustomerOverview/></>}
