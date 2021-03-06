import { IPGraph } from "./IPGraph";
import { IPError } from "./IPErrors";
import { IPStatus } from "./IPStatus";

export class IPWrapper {
    type: 'pipeline' | 'error' | 'reset' | 'status';
    name: string;
    id: string;
    uuid: string;
    source_type: string;
    payload: IPStatus | IPGraph | IPError;

    public constructor(data: any) {
        Object.assign(this, data);
    }
}