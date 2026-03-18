import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { CheckIcon } from "lucide-react";
import "./Checkbox.scss";

const Checkbox = ({ className = "", ...props }) => {
    return (
        <CheckboxPrimitive.Root
            data-slot="checkbox"
            className={`checkbox ${className}`}
            {...props}
        >
            <CheckboxPrimitive.Indicator
                data-slot="checkbox-indicator"
                className="checkbox__indicator"
            >
                <CheckIcon className="checkbox__icon" />
            </CheckboxPrimitive.Indicator>
        </CheckboxPrimitive.Root>
    );
};

export { Checkbox };