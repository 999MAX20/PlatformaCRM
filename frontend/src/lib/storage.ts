const ACCESS_TOKEN_KEY = "ai_smb_access_token";
const USER_EMAIL_KEY = "ai_smb_user_email";

let accessToken: string | null = null;
let sessionGeneration = 0;
let userId: string | null = null;

export const tokenStorage = {
  getGeneration: () => sessionGeneration,
  getUserId: () => userId,
  setUserId: (id: string | number) => { userId = String(id); },
  getAccess: () => accessToken,
  setAccess: (access: string) => {
    accessToken = access;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  },
  clear: () => {
    sessionGeneration += 1;
    userId = null;
    accessToken = null;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(USER_EMAIL_KEY);
  },
  getEmail: () => localStorage.getItem(USER_EMAIL_KEY),
  setEmail: (email: string) => localStorage.setItem(USER_EMAIL_KEY, email),
};
