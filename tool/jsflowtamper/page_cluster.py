from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
import numpy as np
import os
from html_similarity import style_similarity, structural_similarity, similarity
from skimage.measure import compare_ssim
import cv2


def get_dbscan_cluster(tfidf_matrix, epsilon):
    db = DBSCAN(eps=epsilon, min_samples=1).fit(tfidf_matrix)
    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels = db.labels_
    #n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    labels = labels + 1
    return labels.tolist()


def get_dom_sim(pages):
    pageCnt = len(pages)
    matrix = np.zeros(shape=(pageCnt, pageCnt))

    for i in range(pageCnt):
        matrix[i][i] = 1
        for j in range(i + 1, pageCnt):
            sim = structural_similarity(pages[i], pages[j])
            matrix[i][j] = sim
            matrix[j][i] = sim

    return matrix

def get_img_sim(screenshots):
    file_cnt = len(screenshots)

    matrix2 = np.zeros(shape=(file_cnt, file_cnt))
    for i in range(file_cnt):
        #print i,
        #st = time.time()
        matrix2[i][i] = 1
        for j in range(i + 1, file_cnt):
            sim = compare_ssim(screenshots[i], screenshots[j], multichannel=False)
            #sim = compare_ssim(screenshots[i], screenshots[j], multichannel=True)
            matrix2[i][j] = sim
            matrix2[j][i] = sim
        #print time.time() - st

    return matrix2


def perform_clustering(base_path, start_indx, count):
    # load files
    screenshots = []
    pages = []
    filenames = []
    for indx in range(start_indx, start_indx+ count):
        filename = 'test' + str(indx).zfill(4)

        # image
        img_path = base_path + 'screenshot/' + filename + '.jpg'
        if not os.path.isfile(img_path):
            continue


        filenames.append(img_path)

        img = cv2.imread(img_path)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        screenshots.append(gray_img)

        # html
        page_path = base_path + 'html/' + filename + '.html'
        with open(page_path, 'r') as f:
            try:
                body = f.read().decode('utf-8')
            except UnicodeDecodeError:
                print 'unicode error: ' + page_path
                continue

            pages.append(body)

    if len(filenames) == 0:
        print 'No test results available for clustering'
        return

    # calculate sim
    matrix = get_dom_sim(pages)
    lb = get_dbscan_cluster(matrix, 0.085)
    # print lb
    # print 'clusters : ', max(lb)

    matrix2 = get_img_sim(screenshots)
    lb2 = get_dbscan_cluster(matrix2, 0.2)
    # print lb2
    # print 'clusters : ', max(lb2)

    k = 0.15
    matrix3 = ((1 - k) * matrix) + (k * matrix2)
    lb3 = get_dbscan_cluster(matrix3, 0.1)

    cluster_info = []
    for i, filename in enumerate(filenames):
        cluster_info.append([filename, lb3[i]])

    values = set(lb3)
    cluster_info = [[y[0] for y in cluster_info if y[1] == x] for x in values]
    print '=== Test result clustering result ==='
    for i, cluster in enumerate(cluster_info):
        print '[ Cluster', i, ']'
        for filename in cluster:
            id = int(filename[-8:-4])
            print 'Test ID:',id, ', Test Screenshot:', filename


    print '====================================='

    # for i in range(1, 3):
    #     k = 0.3 / float(i)
    #     matrix3 = ((1 - k) * matrix) + (k * matrix2)
    #
    #     lb3 = get_dbscan_cluster(matrix3, 0.1)
    #     print k
    #     print lb3
    #     print max(lb3)
