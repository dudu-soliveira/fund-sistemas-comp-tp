.PHONY: stubs clean

stubs:
	python3 -m grpc_tools.protoc -I. --python_out=. --pyi_out=. \
		--grpc_python_out=. ambulatorio.proto consultorio.proto

clean:
	rm -f *_pb2.py *_pb2_grpc.py *_pb2.pyi *_pb2_grpc.pyi
