.PHONY: stubs clean

stubs: ambulatorio_pb2_grpc.py consultorio_pb2_grpc.py \
		ambulatorio_pb2_grpc.pyi consultorio_pb2_grpc.pyi

%_pb2.py %_pb2.pyi %_pb2_grpc.py %_pb2_grpc.pyi &: %.proto
	python -m grpc_tools.protoc \
		-I. \
		--python_out=. \
		--pyi_out=. \
		--grpc_python_out=. \
		--mypy_grpc_out=. \
		$<

clean:
	rm -f *_pb2.py *_pb2_grpc.py *_pb2.pyi *_pb2_grpc.pyi
