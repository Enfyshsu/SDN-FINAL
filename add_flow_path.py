import json

def add_flow_path(filename, path):
    with open(filename, 'r') as f:
        data = json.load(f)
        data.append(path)

    with open(filename, 'w') as f:    
        json.dump(data, f, indent=4)


def main():
    filename = "flow_path.json"
    n = int(input("Enter device number: "))
    path = {}
    print("Enter main path: ")
    path['main'] = []
    for i in range(n):
        device_id, output_port = input("<device_id output_port>: ").split()
        node = dict({
                "device_id": str(device_id), 
                "output_port": str(output_port)
        })
        
        path['main'].append(node)

    print("Enter backup path: ")
    path['backup'] = []
    for i in range(n):
        device_id, output_port = input("<device_id output_port>: ").split()
        node = dict({
                "device_id": str(device_id), 
                "output_port": str(output_port)
        })
        
        path['backup'].append(node)
    #print(path)   
    add_flow_path(filename, path)


if __name__ == "__main__":
    main()
            

