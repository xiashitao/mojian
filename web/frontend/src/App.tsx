import { Navigate, Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import SessionPage from "./pages/SessionPage";
import OpsPage from "./pages/OpsPage";
import AdminConversationPage from "./pages/AdminConversationPage";
import { ThemeProvider } from "./theme";
import { AuthProvider } from "./auth";

export default function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/session/:conversationId?" element={<SessionPage />} />
          {/* 运营后台(admin only,页面内自守卫):反馈定位 → 会话回放 → 链路 */}
          <Route path="/admin/ops" element={<OpsPage />} />
          <Route
            path="/admin/conversations/:conversationId"
            element={<AdminConversationPage />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ThemeProvider>
    </AuthProvider>
  );
}
