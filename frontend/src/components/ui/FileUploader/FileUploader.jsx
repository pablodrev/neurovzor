import { Upload } from 'lucide-react';
import './FileUploader.scss';

export default function FileUploader({ onFiles }) {
    const handleFileChange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            onFiles(Array.from(e.target.files));
        }
    };

    return (
        <div className="file-uploader">
            <input
                id="file-input"
                type="file"
                accept=".dcm,image/*"
                multiple
                onChange={handleFileChange}
                className="file-uploader__input"
            />
            <label htmlFor="file-input" className="file-uploader__btn">
                <Upload size={18} strokeWidth={1.5} />
                <span>Загрузить</span>
            </label>
        </div>
    );
}