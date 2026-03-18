/**
 * API-сервис для взаимодействия с backend.
 * Обеспечивает загрузку снимков и получение результатов анализа.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

class ApiService {
    constructor(baseUrl = API_BASE) {
        this.baseUrl = baseUrl;
    }

    /**
     * Загружает рентгенограмму на анализ
     * @param {File} file - DICOM, JPG или PNG файл
     * @param {string} patientName - Имя пациента (опционально)
     * @returns {Promise<Object>} Результаты анализа с patient_id
     */
    async analyzeImage(file, patientName = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (patientName) {
            formData.append('patient_name', patientName);
        }

        const response = await fetch(`${this.baseUrl}/hip-dysplasia/analyze`, {
            method: 'POST',
            body: formData,
            // Не устанавливаем Content-Type, браузер сам установит multipart/form-data
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`API Error (${response.status}): ${error}`);
        }

        return response.json();
    }

    /**
     * Получает список всех пациентов
     * @returns {Promise<Array>}
     */
    async getPatients() {
        const response = await fetch(`${this.baseUrl}/patients`, {
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch patients (${response.status})`);
        }

        return response.json();
    }

    /**
     * Получает информацию о конкретном пациенте
     * @param {string} patientId
     * @returns {Promise<Object>}
     */
    async getPatient(patientId) {
        const response = await fetch(`${this.baseUrl}/patients/${patientId}`, {
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch patient (${response.status})`);
        }

        return response.json();
    }

    /**
     * Получает ориентиры (landmarks) для пациента
     * @param {string} patientId
     * @returns {Promise<Array>}
     */
    async getLandmarks(patientId) {
        const response = await fetch(`${this.baseUrl}/patients/${patientId}/landmarks`, {
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch landmarks (${response.status})`);
        }

        return response.json();
    }

    /**
     * Получает результаты анализа для пациента
     * @param {string} patientId
     * @returns {Promise<Array>}
     */
    async getResults(patientId) {
        const response = await fetch(`${this.baseUrl}/patients/${patientId}/results`, {
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch results (${response.status})`);
        }

        return response.json();
    }

    /**
     * Получает уверенность диагноза
     * @param {string} patientId
     * @returns {Promise<Object>} { value: number }
     */
    async getConfidence(patientId) {
        const response = await fetch(`${this.baseUrl}/patients/${patientId}/confidence`, {
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch confidence (${response.status})`);
        }

        return response.json();
    }

    /**
     * Получает информацию о модуле ТБС
     * @returns {Promise<Object>}
     */
    async getModuleInfo() {
        const response = await fetch(`${this.baseUrl}/hip-dysplasia/info`, {
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch module info (${response.status})`);
        }

        return response.json();
    }

    /**
     * Проверяет доступность API
     * @returns {Promise<boolean>}
     */
    async healthCheck() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return response.ok;
        } catch {
            return false;
        }
    }
}

export default new ApiService();
