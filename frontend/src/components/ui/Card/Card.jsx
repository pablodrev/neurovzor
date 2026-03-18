import "./Card.scss";

const Card = ({ className = "", children, ...props }) => {
    return (
        <div
            data-slot="card"
            className={`card ${className}`}
            {...props}
        >
            {children}
        </div>
    );
};

const CardHeader = ({ className = "", children, ...props }) => {
    return (
        <div
            data-slot="card-header"
            className={`card__header ${className}`}
            {...props}
        >
            {children}
        </div>
    );
};

const CardTitle = ({ className = "", children, ...props }) => {
    return (
        <h4
            data-slot="card-title"
            className={`card__title ${className}`}
            {...props}
        >
            {children}
        </h4>
    );
};

const CardDescription = ({ className = "", children, ...props }) => {
    return (
        <p
            data-slot="card-description"
            className={`card__description ${className}`}
            {...props}
        >
            {children}
        </p>
    );
};

const CardAction = ({ className = "", children, ...props }) => {
    return (
        <div
            data-slot="card-action"
            className={`card__action ${className}`}
            {...props}
        >
            {children}
        </div>
    );
};

const CardContent = ({ className = "", children, ...props }) => {
    return (
        <div
            data-slot="card-content"
            className={`card__content ${className}`}
            {...props}
        >
            {children}
        </div>
    );
};

const CardFooter = ({ className = "", children, ...props }) => {
    return (
        <div
            data-slot="card-footer"
            className={`card__footer ${className}`}
            {...props}
        >
            {children}
        </div>
    );
};

export {
    Card,
    CardHeader,
    CardFooter,
    CardTitle,
    CardAction,
    CardDescription,
    CardContent,
};