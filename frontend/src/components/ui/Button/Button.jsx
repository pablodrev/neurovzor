import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import "./Button.scss";

const Button = ({
    className = "",
    variant = "default",
    size = "default",
    asChild = false,
    children,
    ...props
}) => {
    const Comp = asChild ? Slot : "button";

    return (
        <Comp
            data-slot="button"
            className={`btn btn--${variant} btn--${size} ${className}`}
            {...props}
        >
            {children}
        </Comp>
    );
};

export { Button };