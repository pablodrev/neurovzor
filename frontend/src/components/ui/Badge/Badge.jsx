import { Slot } from "@radix-ui/react-slot";
import "./Badge.scss";

const Badge = ({
    className = "",
    variant = "default",
    asChild = false,
    children,
    ...props
}) => {
    const Comp = asChild ? Slot : "span";

    return (
        <Comp
            data-slot="badge"
            className={`badge badge--${variant} ${className}`}
            {...props}
        >
            {children}
        </Comp>
    );
};

export { Badge };