import { log } from "./logger.js";

interface Config {
    name: string;
    version: string;
    patterns: {
        GObjects: string;
        GNames: string;
        GWorld: string;
    };
    offsets: {
        UObject: {
            ClassPrivate: number;
            NamePrivate: number;
            OuterPrivate: number;
        };
        UField: {
            Next: number;
        };
        UProperty: {
            Offset_Internal: number;
        };
        FUObjectArray: {
            NumElements: number;
            MaxElements: number;
            Objects: number;
        };
        FNameEntry: {
            Index: number;
            String: number;
        };
        UStruct: {
            SuperStruct: number;
            Children: number;
            PropertiesSize: number;
            MinAlignment: number;
        };
        UClass: {
            CastFlags: number;
            ClassDefaultObject: number;
        };
    };
}

class UEExplorer {
    private config: Config | null = null;
    private baseModule: Module | null = null;
    private GObjects: NativePointer | null = null;
    private GNames: NativePointer | null = null;
    private GWorld: NativePointer | null = null;

    initialize(configData: string): boolean {
        try {
            this.config = JSON.parse(configData);
            this.baseModule = Process.enumerateModules()[0];
            log(`[+] Initialized with config: ${this.config!.name}`);
            log(`[+] Base module: ${this.baseModule!.name} at ${this.baseModule!.base}`);
            
            if (!this.findGlobals()) {
                log("[-] Failed to find UE globals");
                return false;
            }
            
            log("[+] UE Explorer initialized successfully");
            return true;
        } catch (error) {
            log(`[-] Failed to initialize: ${error}`);
            return false;
        }
    }

    private findGlobals(): boolean {
        if (!this.config || !this.baseModule) return false;

        try {
            this.GObjects = this.findPatternAddress(this.config.patterns.GObjects);
            this.GNames = this.findPatternAddress(this.config.patterns.GNames);
            this.GWorld = this.findPatternAddress(this.config.patterns.GWorld);

            if (this.GObjects && this.GNames && this.GWorld) {
                log(`[+] GObjects: ${this.GObjects}`);
                log(`[+] GNames: ${this.GNames}`);
                log(`[+] GWorld: ${this.GWorld}`);
                return true;
            }
            return false;
        } catch (error) {
            log(`[-] Error finding globals: ${error}`);
            return false;
        }
    }

    private findPatternAddress(pattern: string): NativePointer | null {
        if (!this.baseModule) return null;

        try {
            const ranges = Process.enumerateRanges('r-x').filter(range => 
                range.base.compare(this.baseModule!.base) >= 0 && 
                range.base.compare(this.baseModule!.base.add(this.baseModule!.size)) < 0
            );

            for (const range of ranges) {
                const results = Memory.scanSync(range.base, range.size, pattern);
                if (results.length > 0) {
                    const address = results[0].address;
                    const offset = address.add(3).readS32();
                    const resolvedAddress = address.add(7).add(offset);
                    return resolvedAddress.readPointer();
                }
            }
            return null;
        } catch (error) {
            log(`[-] Pattern scan error: ${error}`);
            return null;
        }
    }

    getInfo(): any {
        if (!this.GObjects || !this.GNames || !this.GWorld || !this.config) {
            return { error: "Not initialized" };
        }

        try {
            const gobjectsArray = this.GObjects.readPointer();
            const numElements = gobjectsArray.add(this.config.offsets.FUObjectArray.NumElements).readU32();
            
            return {
                GObjects: this.GObjects.toString(),
                GNames: this.GNames.toString(),
                GWorld: this.GWorld.toString(),
                ObjectCount: numElements
            };
        } catch (error: any) {
            return { error: error.toString() };
        }
    }

    dumpObject(address: string): any {
        if (!this.config) return { error: "Not initialized" };

        try {
            const objPtr = ptr(address);
            if (objPtr.isNull()) return { error: "Invalid address" };

            return this.dumpUObject(objPtr);
        } catch (error: any) {
            return { error: error.toString() };
        }
    }

    private dumpUObject(objPtr: NativePointer): any {
        if (!this.config || objPtr.isNull()) return null;

        try {
            const nameIndex = objPtr.add(this.config.offsets.UObject.NamePrivate).readU32();
            const classPtr = objPtr.add(this.config.offsets.UObject.ClassPrivate).readPointer();
            const outerPtr = objPtr.add(this.config.offsets.UObject.OuterPrivate).readPointer();

            const name = this.getObjectName(nameIndex);
            const className = classPtr.isNull() ? "Unknown" : this.getObjectName(classPtr.add(this.config.offsets.UObject.NamePrivate).readU32());

            const result: any = {
                Address: objPtr.toString(),
                Name: name,
                Class: className,
                Outer: outerPtr.isNull() ? null : outerPtr.toString()
            };

            if (!classPtr.isNull()) {
                result.Properties = this.dumpObjectProperties(objPtr, classPtr);
            }

            return result;
        } catch (error: any) {
            return { error: error.toString() };
        }
    }

    private dumpObjectProperties(objPtr: NativePointer, classPtr: NativePointer): any[] {
        if (!this.config) return [];

        const properties: any[] = [];
        try {
            let currentField = classPtr.add(this.config.offsets.UStruct.Children).readPointer();
            
            while (!currentField.isNull()) {
                try {
                    const propName = this.getObjectName(currentField.add(this.config.offsets.UObject.NamePrivate).readU32());
                    const propClass = currentField.add(this.config.offsets.UObject.ClassPrivate).readPointer();
                    const propClassName = propClass.isNull() ? "Unknown" : this.getObjectName(propClass.add(this.config.offsets.UObject.NamePrivate).readU32());
                    
                    const offset = currentField.add(this.config.offsets.UProperty.Offset_Internal).readU32();
                    
                    properties.push({
                        Name: propName,
                        Type: propClassName,
                        Offset: offset,
                        Address: currentField.toString()
                    });

                    currentField = currentField.add(this.config.offsets.UField.Next).readPointer();
                } catch (error) {
                    break;
                }
            }
        } catch (error) {
            log(`[-] Error dumping properties: ${error}`);
        }

        return properties;
    }

    private getObjectName(nameIndex: number): string {
        if (!this.GNames || !this.config) return "Unknown";

        try {
            const nameArray = this.GNames;
            const nameEntry = nameArray.add(nameIndex * Process.pointerSize).readPointer();
            
            if (nameEntry.isNull()) return "Unknown";
            
            const nameStr = nameEntry.add(this.config.offsets.FNameEntry.String).readUtf8String();
            return nameStr || "Unknown";
        } catch (error) {
            return "Unknown";
        }
    }

    findObjects(searchName: string): any[] {
        if (!this.GObjects || !this.config) return [];

        const results: any[] = [];
        try {
            const gobjectsArray = this.GObjects.readPointer();
            const numElements = gobjectsArray.add(this.config.offsets.FUObjectArray.NumElements).readU32();
            const objectsPtr = gobjectsArray.add(this.config.offsets.FUObjectArray.Objects).readPointer();

            for (let i = 0; i < Math.min(numElements, 100000); i++) {
                try {
                    const objPtr = objectsPtr.add(i * Process.pointerSize).readPointer();
                    if (objPtr.isNull()) continue;

                    const nameIndex = objPtr.add(this.config.offsets.UObject.NamePrivate).readU32();
                    const name = this.getObjectName(nameIndex);
                    
                    if (name.toLowerCase().includes(searchName.toLowerCase())) {
                        const classPtr = objPtr.add(this.config.offsets.UObject.ClassPrivate).readPointer();
                        const className = classPtr.isNull() ? "Unknown" : this.getObjectName(classPtr.add(this.config.offsets.UObject.NamePrivate).readU32());
                        
                        results.push({
                            Address: objPtr.toString(),
                            Name: name,
                            Class: className,
                            Index: i
                        });

                        if (results.length >= 50) break;
                    }
                } catch (error) {
                    continue;
                }
            }
        } catch (error) {
            log(`[-] Error finding objects: ${error}`);
        }

        return results;
    }

    findObjectsByClass(className: string): any[] {
        if (!this.GObjects || !this.config) return [];

        const results: any[] = [];
        try {
            const gobjectsArray = this.GObjects.readPointer();
            const numElements = gobjectsArray.add(this.config.offsets.FUObjectArray.NumElements).readU32();
            const objectsPtr = gobjectsArray.add(this.config.offsets.FUObjectArray.Objects).readPointer();

            for (let i = 0; i < Math.min(numElements, 100000); i++) {
                try {
                    const objPtr = objectsPtr.add(i * Process.pointerSize).readPointer();
                    if (objPtr.isNull()) continue;

                    const classPtr = objPtr.add(this.config.offsets.UObject.ClassPrivate).readPointer();
                    if (classPtr.isNull()) continue;

                    const objClassName = this.getObjectName(classPtr.add(this.config.offsets.UObject.NamePrivate).readU32());
                    
                    if (objClassName.toLowerCase().includes(className.toLowerCase())) {
                        const nameIndex = objPtr.add(this.config.offsets.UObject.NamePrivate).readU32();
                        const name = this.getObjectName(nameIndex);
                        
                        results.push({
                            Address: objPtr.toString(),
                            Name: name,
                            Class: objClassName,
                            Index: i
                        });

                        if (results.length >= 50) break;
                    }
                } catch (error) {
                    continue;
                }
            }
        } catch (error) {
            log(`[-] Error finding objects by class: ${error}`);
        }

        return results;
    }

    dumpWorld(): any {
        if (!this.GWorld) return { error: "GWorld not found" };

        try {
            const worldPtr = this.GWorld.readPointer();
            if (worldPtr.isNull()) return { error: "GWorld is null" };

            return this.dumpUObject(worldPtr);
        } catch (error: any) {
            return { error: error.toString() };
        }
    }
}

const explorer = new UEExplorer();

rpc.exports = {
    init: function(configData: string): boolean {
        return explorer.initialize(configData);
    },
    info: function(): any {
        return explorer.getInfo();
    },
    dump: function(address: string): any {
        return explorer.dumpObject(address);
    },
    world: function(): any {
        return explorer.dumpWorld();
    },
    find: function(name: string): any[] {
        return explorer.findObjects(name);
    },
    findclass: function(className: string): any[] {
        return explorer.findObjectsByClass(className);
    }
};

log("[+] Frida UE Explorer Agent loaded");