from glassflow import GlassFlowClient
import os
from dotenv import load_dotenv

load_dotenv()

class GlassFlowSource:
    def __init__(self, access_token: str):
        self.client = GlassFlowClient(personal_access_token=access_token)
        self.space = self.client.create_space("news")
        self.pipeline = self.client.get_pipeline(pipeline_id=os.getenv("GLASSFLOW_PIPELINE_ID"))
        self.data_source = self.pipeline.get_source()
        self.data_sink = self.pipeline.get_sink()



############ Example usage ############
# client = GlassFlowClient(personal_access_token=glassflow_token)

# space = client.create_space("news")

# pipline = client.create_pipeline(name="news_pipline", space_id=space.id, transformation_file="transformation.py")

# data_source = pipline.get_source()

# input_data = []
# for i in range(5):
#     d = random_datagen()
#     input_data.append(d)
#     r = data_source.publish(d)


# for dt in input_data:
#     #print(dt)

# #print("-"*50)

# data_sink = pipline.get_sink()

# output = []

# for i in range(5):
#     d = data_sink.consume()
#     output.append(d.json())

# for op in output:
#     #print(op)

