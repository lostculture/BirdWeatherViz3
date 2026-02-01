/**
 * API Client
 * Axios-based HTTP client for backend API communication.
 *
 * Version: 1.0.0
 */

import axios, { AxiosError, AxiosInstance, AxiosResponse } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

class APIClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor for adding auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Clear token on 401 - let components handle auth state
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_token_expiry')
          // Don't redirect - let components show password modal
        }
        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, params?: Record<string, any>): Promise<T> {
    const response: AxiosResponse<T> = await this.client.get(url, { params })
    return response.data
  }

  async post<T>(url: string, data?: Record<string, any>, config?: Record<string, any>): Promise<T> {
    const response: AxiosResponse<T> = await this.client.post(url, data, {
      ...config,
      timeout: config?.timeout || 30000,
    })
    return response.data
  }

  async put<T>(url: string, data?: Record<string, any>): Promise<T> {
    const response: AxiosResponse<T> = await this.client.put(url, data)
    return response.data
  }

  async delete<T>(url: string): Promise<T> {
    const response: AxiosResponse<T> = await this.client.delete(url)
    return response.data
  }
}

export const apiClient = new APIClient()
