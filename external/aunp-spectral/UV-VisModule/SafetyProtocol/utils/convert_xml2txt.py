import pandas as pd
import natsort
import os


def get_attributes(file):
    info_df = pd.read_json(file)
    info_df = info_df.transpose().reset_index()[['filename', 'regions']]
    info = []

    info.append(info_df['filename'][0])
    for row in range(info_df.shape[0]):
        for col in range(len(info_df['regions'][row])):
            data_c = info_df['regions'][row][col]['region_attributes']['class']
            # if int(data_c) == 0:
            if str(data_c) == 'pin':
                data_x = info_df['regions'][row][col]['shape_attributes']['x']
                data_y = info_df['regions'][row][col]['shape_attributes']['y']
                data_w = info_df['regions'][row][col]['shape_attributes']['width']
                data_h = info_df['regions'][row][col]['shape_attributes']['height']

                info.append(data_x)
                info.append(data_y)
                info.append(data_w)
                info.append(data_h)
                info.append(int(1))
            # elif int(data_c) == 1:
            #     data_x = info_df['regions'][row][col]['shape_attributes']['x']
            #     data_y = info_df['regions'][row][col]['shape_attributes']['y']
            #     data_w = info_df['regions'][row][col]['shape_attributes']['width']
            #
            #     info.append(data_x)
            #     info.append(data_y)
            #     info.append(data_w)
            #     info.append(data_w)
            #     info.append(int(data_c))

    return info


if __name__ == '__main__':
    path = '../our_dataset/Info'
    text_file = '../pinStorage.txt'

    folder = os.listdir(path)
    folder = natsort.natsorted(folder)

    f = open(text_file, "w")

    for folder_name in folder:
        filename = os.listdir(os.path.join(path, folder_name))

        filename = natsort.natsorted(filename)
        for file in filename:
            p = os.path.join(path + '/' + folder_name, file)
            print(p)
            json_info = get_attributes(p)

            for i in range(len(json_info)):
                if i == 0:
                    f.write(str(folder_name + '/' + json_info[i]) + " ")
                elif i == len(json_info)-1:
                    f.write(str(json_info[i]))
                else:
                    f.write(str(json_info[i]) + " ")
            f.write("\n")
    f.close()
