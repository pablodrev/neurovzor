import "./Input.scss";

const Input = ({ className = "", type = "text", ...props }) => {
    return (
        <input
            type={type}
            data-slot="input"
            className={`input ${className}`}
            {...props}
        />
    );
};

export { Input };