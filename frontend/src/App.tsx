import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout";
import { CommandPalette } from "./components/CommandPalette";
import { ToastHost } from "./components/ToastHost";
import { useSimulation } from "./hooks/useSimulation";
import Analytics from "./pages/Analytics";
import AIDecisions from "./pages/AIDecisions";
import CommandCenter from "./pages/CommandCenter";
import Courier from "./pages/Courier";
import Curb from "./pages/Curb";
import Fleet from "./pages/Fleet";
import HubPortal from "./pages/HubPortal";
import Hubs from "./pages/Hubs";
import Impact from "./pages/Impact";
import JudgeView from "./pages/JudgeView";
import Landing from "./pages/Landing";
import LiveOps from "./pages/LiveOps";
import Orders from "./pages/Orders";
import Simulation from "./pages/Simulation";
import DemoStepper from "./features/demo/DemoStepper";
import ExtensionGuide from "./pages/ExtensionGuide";

export default function App() {
  useSimulation();
  return (
    <>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/demo" element={<DemoStepper />} />
        <Route path="/app" element={<AppShell />}>
          <Route index element={<CommandCenter />} />
          <Route path="live" element={<LiveOps />} />
          <Route path="orders" element={<Orders />} />
          <Route path="hubs" element={<Hubs />} />
          <Route path="hub-portal" element={<HubPortal />} />
          <Route path="courier" element={<Courier />} />
          <Route path="fleet" element={<Fleet />} />
          <Route path="curb" element={<Curb />} />
          <Route path="ai" element={<AIDecisions />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="simulation" element={<Simulation />} />
          <Route path="judge" element={<JudgeView />} />
          <Route path="impact" element={<Impact />} />
          <Route path="extension" element={<ExtensionGuide />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <CommandPalette />
      <ToastHost />
    </>
  );
}