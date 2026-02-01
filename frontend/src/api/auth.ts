/**
 * Authentication API
 * Functions for login, logout, and token management.
 *
 * Version: 1.0.0
 */

import { apiClient } from './client'

const TOKEN_KEY = 'auth_token'
const TOKEN_EXPIRY_KEY = 'auth_token_expiry'

interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

interface PasswordStatusResponse {
  is_custom: boolean
  message: string
}

interface ChangePasswordResponse {
  success: boolean
  message: string
}

export const authApi = {
  /**
   * Login with configuration password.
   * On success, stores token in localStorage.
   */
  login: async (password: string): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', { password })

    // Store token and expiry
    localStorage.setItem(TOKEN_KEY, response.access_token)
    const expiryTime = Date.now() + (response.expires_in * 1000)
    localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString())

    return response
  },

  /**
   * Logout - clears stored token.
   */
  logout: (): void => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(TOKEN_EXPIRY_KEY)
  },

  /**
   * Check if user is authenticated (has valid, non-expired token).
   */
  isAuthenticated: (): boolean => {
    const token = localStorage.getItem(TOKEN_KEY)
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY)

    if (!token || !expiry) {
      return false
    }

    const expiryTime = parseInt(expiry, 10)
    if (isNaN(expiryTime)) {
      return false
    }

    // Check if token is expired (with 60 second buffer)
    if (Date.now() >= expiryTime - 60000) {
      // Token expired, clear it
      authApi.logout()
      return false
    }

    return true
  },

  /**
   * Get stored token (or null if not authenticated).
   */
  getToken: (): string | null => {
    if (!authApi.isAuthenticated()) {
      return null
    }
    return localStorage.getItem(TOKEN_KEY)
  },

  /**
   * Get password status (whether custom password is set).
   */
  getPasswordStatus: async (): Promise<PasswordStatusResponse> => {
    return apiClient.get<PasswordStatusResponse>('/auth/password-status')
  },

  /**
   * Change the configuration password.
   */
  changePassword: async (currentPassword: string, newPassword: string): Promise<ChangePasswordResponse> => {
    return apiClient.put<ChangePasswordResponse>('/auth/password', {
      current_password: currentPassword,
      new_password: newPassword
    })
  }
}
