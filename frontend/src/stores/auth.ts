import { create } from "zustand";
import { api, setToken } from "../services/api";

interface AuthState {
  token: string | null;
  role: string | null;
  username: string | null;
  fullName: string | null;
  login: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("ur_token"),
  role: localStorage.getItem("ur_role"),
  username: localStorage.getItem("ur_username"),
  fullName: localStorage.getItem("ur_fullname"),

  login: async () => {
    const res = await api.loginDemo();
    setToken(res.access_token);
    localStorage.setItem("ur_role", res.role);
    localStorage.setItem("ur_username", res.username);
    localStorage.setItem("ur_fullname", res.full_name);
    set({ token: res.access_token, role: res.role, username: res.username, fullName: res.full_name });
  },

  logout: () => {
    setToken(null);
    localStorage.removeItem("ur_role");
    localStorage.removeItem("ur_username");
    localStorage.removeItem("ur_fullname");
    set({ token: null, role: null, username: null, fullName: null });
  },
}));