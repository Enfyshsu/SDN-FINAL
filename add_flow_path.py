import json

def add_flow_path(filename, path):
    with open(filename, 'r') as f:
        data = json.load(f)
        data.append(path)

    with open(filename, 'w') as f:    
        json.dump(data, f, indent=4)

def inputPath(n, path, kind):
    path[kind] = []
    for i in range(n):
        device_id, output_port = input("<device_id> <output_port>: ").split()
        node = dict({
                "device_id": str(device_id), 
                "output_port": str(output_port)
        })
        
        path[kind].append(node)

def main():
    filename = "flow_path_2.json"
    path = {}
    src_host = input("Enter source host: ")
    dst_host = input("Enter destination host: ")
    path['src_ip'] = "10.0.0." + src_host
    path['dst_ip'] = "10.0.0." + dst_host

    n = int(input("Enter main path device number: "))
    print("Enter main path: ")
    inputPath(n, path, 'main_A')

    print("Enter main_B path: ")
    inputPath(n, path, 'main_B')

    n = int(input("Enter backup path device number: "))
    print("Enter backup_A path: ")
    inputPath(n, path, 'backup_A')

    print("Enter backup_B path: ")
    inputPath(n, path, 'backup_B')
    
    #print(path)   
    add_flow_path(filename, path)


if __name__ == "__main__":
    main()
            

